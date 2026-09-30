# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The ot11 contract reader, on gaits, reaches and balances whose answers are stated.

``docs/probes/ot11/runner/measure.py`` is what measured the known negatives
(ot10's ``w2-2`` shuffle, ot9's Robin) against the frozen specs. The reading
itself is the product's (``CadexEvaluation``, ADR-455, pinned metric by metric
in ``cadex_tests/test_evaluation_metrics.py``); what is pinned here is the
**binding**: that each frozen predicate, W1-W10, Q1-Q4 and B1-B5, passes on a
motion that meets it and fails on one that does not, for the stated reason.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
OT11 = REPO / "docs/probes/ot11"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


measure = _load("ot11_measure", OT11 / "runner/measure.py")
# The stated motions are the engine suite's, so the contract is read on the
# same fixtures the product's metrics are pinned on.
fixtures = _load("evaluation_fixtures", REPO / "src/Mod/cadex/cadex_tests/evaluation_fixtures.py")

DONE, REACH_DONE, SHOVES = fixtures.DONE, fixtures.REACH_DONE, fixtures.SHOVES
walk_rig, balance_rig, reach_rig = fixtures.walk_rig, fixtures.balance_rig, fixtures.reach_rig
trot, shuffle, standing, reaching, pitch = (fixtures.trot, fixtures.shuffle, fixtures.standing,
                                            fixtures.reaching, fixtures.pitch)


def verdict(result):
    return {row["id"]: row["pass"] for row in result["predicates"]}


def failing(result):
    return sorted(row["id"] for row in result["predicates"] if row["pass"] is False)


# -- walk -------------------------------------------------------------------

def test_a_trot_with_real_steps_passes_every_walk_predicate() -> None:
    result = measure.walk(trot(), walk_rig(), 80.0, DONE)
    assert verdict(result) == {f"W{i}": True for i in range(1, 11)}
    feet = result["metrics"]["feet"]
    for foot in feet.values():
        assert 19 <= foot["steps"] <= 21  # 10 s at 0.48 s a cycle
        assert foot["median_step_clearance_mm"] == pytest.approx(15.0, abs=0.2)
        assert foot["duty_factor"] == pytest.approx(0.5, abs=0.03)
        assert foot["slip_share"] == pytest.approx(0.0, abs=1e-9)
        assert foot["step_share"] > 0.95
    assert result["metrics"]["mean_forward_speed_mm_s"] == pytest.approx(80.0, abs=0.5)


def test_a_shuffle_fails_on_stepping_and_clearance_and_not_on_staying_up() -> None:
    result = measure.walk(shuffle(), walk_rig(), 140.0, DONE)
    assert failing(result) == ["W5", "W6", "W7", "W9"]
    assert verdict(result)["W1"] and verdict(result)["W2"] and verdict(result)["W3"]
    for foot in result["metrics"]["feet"].values():
        assert foot["swings"] > 100 and foot["steps"] == 0
        assert foot["median_swing_peak_mm"] == pytest.approx(2.5)


def test_feet_dragged_along_the_floor_fail_slip_and_duty_factor() -> None:
    result = measure.walk(shuffle(hop=0.0), walk_rig(), 140.0, DONE)
    assert failing(result) == ["W5", "W6", "W7", "W8", "W9"]
    for foot in result["metrics"]["feet"].values():
        assert foot["slip_share"] == pytest.approx(1.0)
        assert foot["duty_factor"] == 1.0


def test_steps_that_barely_clear_the_floor_fail_clearance_alone() -> None:
    result = measure.walk(trot(lift=5.0), walk_rig(), 80.0, DONE)
    assert failing(result) == ["W6"]  # 5 mm on a 100 mm hip: 0.05 < 0.08


def test_feet_driven_into_the_floor_fail_w10_alone() -> None:
    # w2-2's other shape: real steps, but the stance foot sits most of a foot
    # radius inside a floor that soft contact let it enter.
    assert failing(measure.walk(trot(sink=4.0), walk_rig(), 80.0, DONE)) == []
    result = measure.walk(trot(sink=6.0), walk_rig(), 80.0, DONE)
    assert failing(result) == ["W10"]  # 6 mm on a 100 mm hip: -0.06 < -0.05
    assert result["metrics"]["sink_limit_mm"] == pytest.approx(-5.0)


def test_an_episode_that_ends_inside_the_settle_fails_with_nothing_measured() -> None:
    ended = {**DONE, "termination": "tipped", "truncated": False, "duration_s": 0.84}
    result = measure.walk(trot(seconds=0.84), walk_rig(), 80.0, ended)
    rows = {row["id"]: row for row in result["predicates"]}
    assert rows["W3"]["pass"] is False and rows["W3"]["value"] is None
    assert "settle" in rows["W3"]["why"] and rows["W8"]["pass"] is False
    json.dumps(result, allow_nan=False)  # no NaN reaches the report


def test_the_wrong_speed_fails_tracking_alone() -> None:
    assert failing(measure.walk(trot(speed=80.0), walk_rig(), 50.0, DONE)) == ["W3"]
    assert failing(measure.walk(trot(speed=80.0), walk_rig(), 120.0, DONE)) == ["W3"]


def test_a_veer_fails_going_straight() -> None:
    assert failing(measure.walk(trot(heading=6.0), walk_rig(), 80.0, DONE)) == ["W4"]


def test_a_foot_that_mostly_hangs_in_the_air_fails_duty_factor() -> None:
    result = measure.walk(trot(swing_frames=18), walk_rig(), 80.0, DONE)
    assert failing(result) == ["W8"]  # duty 0.25


def test_a_tumble_fails_upright_and_an_early_end_fails_completes() -> None:
    samples = trot()
    samples[200][1]["base"]["rotation_xyzw"] = pitch(40.0)
    assert "W2" in failing(measure.walk(samples, walk_rig(), 80.0, DONE))
    ended = {**DONE, "termination": "tipped", "truncated": False, "duration_s": 4.0}
    assert "W1" in failing(measure.walk(trot(seconds=4.0), walk_rig(), 80.0, ended))


def test_an_off_contract_horizon_is_not_measured_rather_than_passed_or_failed() -> None:
    eight = {**DONE, "duration_s": 8.0}
    row = measure.walk(trot(seconds=8.0), walk_rig(), 80.0, eight, off_contract=True)["predicates"][0]
    assert row["pass"] is None and "8.0 s" in row["why"]
    assert measure.walk(trot(seconds=8.0), walk_rig(), 80.0, eight)["predicates"][0]["pass"] is False


def test_the_w2_2_shuffle_fails_the_walk_spec_for_the_reasons_the_contract_records() -> None:
    # The known negative, as a fixture: the base and feet of ot10's stored
    # w2-2 rollout. It must fail, and on stepping and slip -- not by accident.
    samples, rig, command, episode = fixtures.w2_2()
    result = measure.walk(samples, rig, command, episode, off_contract=True)
    recorded = measure.contract()["known_negatives"]["walk_w2_2"]
    assert failing(result) == sorted(recorded["failing"]) == ["W10", "W3", "W5", "W7", "W9"]
    assert sorted(row["id"] for row in result["predicates"] if row["pass"]) == sorted(recorded["passing"])
    feet = result["metrics"]["feet"]
    for key in ("steps", "swings"):
        assert [feet[name][key] for name in recorded["feet"]] == recorded[key]
    for key, places in (("step_share", 2), ("slip_share", 2), ("duty_factor", 2), ("lowest_height_mm", 1),
                        ("median_step_clearance_mm", 1), ("median_swing_peak_mm", 1)):
        assert [round(feet[name][key], places) for name in recorded["feet"]] == recorded[key], key
    rows = {row["id"]: row for row in result["predicates"]}
    assert "step_share_min is 0.1396, under 0.7" in rows["W5"]["why"]
    assert "slip_share_max is 0.6659, over 0.15" in rows["W7"]["why"]


# -- reach ------------------------------------------------------------------

def reach(samples, episode=REACH_DONE, **kwargs):
    return measure.reach(samples, reach_rig(), fixtures.segments(), episode, **kwargs)


def test_a_direct_reach_to_both_targets_passes_every_reach_predicate() -> None:
    result = reach(reaching())
    assert verdict(result) == {f"Q{i}": True for i in range(1, 5)}
    rows = {row["id"]: row for row in result["predicates"]}
    assert rows["Q3"]["value"] == pytest.approx([0.96, 0.92]) and rows["Q3"]["limit"] == {"max_s": 2.0}
    assert rows["Q2"]["limit"] == {"max": 0.05} and rows["Q4"]["limit"] == {"max": 0.2}


def test_a_swing_past_the_target_fails_overshoot_alone() -> None:
    result = reach(reaching(over=0.3))
    assert failing(result) == ["Q4"]
    assert result["metrics"]["overshoot_ratio_max"] == pytest.approx(0.3)
    assert failing(reach(reaching(over=0.15))) == []  # inside the 0.20 the contract allows


def test_a_slow_reach_fails_time_alone_and_one_that_stops_short_fails_error_and_time() -> None:
    assert failing(reach(reaching(move_s=3.0))) == ["Q3"]
    short = reach(reaching(miss_mm=20.0))  # 0.10 arm lengths short, limit 0.05
    assert failing(short) == ["Q2", "Q3"]
    assert {row["id"]: row for row in short["predicates"]}["Q3"]["value"] == [None, None]
    assert failing(reach(reaching(miss_mm=8.0))) == []  # 0.04 arm lengths


def test_a_reach_that_holds_one_target_and_not_the_other_fails() -> None:
    assert failing(reach(reaching(leaves_at=7.0))) == ["Q2", "Q3"]


def test_a_reach_episode_that_ends_early_fails_completes() -> None:
    ended = {**REACH_DONE, "termination": "collided", "truncated": False, "duration_s": 2.0}
    assert "Q1" in failing(reach(reaching(), ended))
    ten = {**REACH_DONE, "duration_s": 10.0}
    assert reach(reaching(), ten, off_contract=True)["predicates"][0]["pass"] is None


# -- balance ----------------------------------------------------------------

def test_a_balancer_that_stays_put_and_recovers_passes_every_balance_predicate() -> None:
    result = measure.balance(standing(), balance_rig(), SHOVES, DONE)
    assert verdict(result) == {f"B{i}": True for i in range(1, 6)}
    assert result["metrics"]["max_drift_mm"] == pytest.approx(20.0, abs=0.5)
    assert all(0.0 <= t <= 2.0 for t in result["metrics"]["recovery_s"])


def test_a_balancer_that_wanders_off_fails_staying_in_place() -> None:
    # Robin's ot9 shape: upright all episode, 105 mm/s in one direction.
    result = measure.balance(standing(drift=105.0, shoves=()), balance_rig(), [], {**DONE, "duration_s": 8.0},
                             off_contract=True)
    assert failing(result) == ["B3"]
    assert [row["id"] for row in result["predicates"] if row["pass"] is None] == ["B1", "B5"]
    assert result["metrics"]["max_drift_mm"] == pytest.approx(1050.0, rel=0.01)


def test_a_balancer_that_turns_fails_heading_alone() -> None:
    assert failing(measure.balance(standing(turn=5.0), balance_rig(), SHOVES, DONE)) == ["B4"]


def test_a_shove_it_never_settles_from_fails_recovery() -> None:
    slow = measure.balance(standing(settle=3.0, lean=25.0), balance_rig(), SHOVES, DONE)
    assert "B5" in failing(slow)
    # Upright but never at rest: rolling at over one COM height (50 mm) a second.
    rolling = measure.balance(standing(drift=60.0, lean=2.0), balance_rig(), SHOVES, DONE)
    assert failing(rolling) == ["B3", "B5"]
    assert rolling["metrics"]["recovery_s"] == [None, None]


def test_a_fall_fails_upright() -> None:
    assert "B2" in failing(measure.balance(standing(lean=45.0), balance_rig(), SHOVES, DONE))


# -- the binding ------------------------------------------------------------

def test_every_frozen_predicate_is_bound_to_a_metric_the_product_measures() -> None:
    measured = {
        "walk": measure.walk(trot(), walk_rig(), 80.0, DONE)["metrics"],
        "reach": reach(reaching())["metrics"],
        "balance": measure.balance(standing(), balance_rig(), SHOVES, DONE)["metrics"],
    }
    for behaviour, block in measure.contract()["behaviours"].items():
        ids = [row["id"] for row in block["predicates"]]
        # The first predicate of each behaviour is "completes", read from the
        # episode; every other one is a bound on a product metric.
        assert sorted(measure.BINDING[behaviour]) == sorted(ids[1:]), behaviour
        for identifier in ids[1:]:
            for row in measure.spec(behaviour, identifier):
                assert row["metric"] in measured[behaviour], (identifier, row["metric"])
                assert row["min"] is not None or row["max"] is not None, identifier
    assert measure.spec("walk", "W5") == [
        {"id": "W5", "metric": "steps_min", "min": 4, "max": None},
        {"id": "W5", "metric": "step_share_min", "min": 0.7, "max": None}]
    assert measure.spec("walk", "W8") == [
        {"id": "W8", "metric": "duty_factor_min", "min": 0.4, "max": 0.85},
        {"id": "W8", "metric": "duty_factor_max", "min": 0.4, "max": 0.85}]
    assert measure.spec("reach", "Q3") == [{"id": "Q3", "metric": "time_to_target_s_max", "min": None, "max": 2.0}]
    assert measure.spec("balance", "B5") == [{"id": "B5", "metric": "recovery_s_max", "min": None, "max": 2.0}]


def test_the_contracts_definitions_are_the_numbers_the_reader_is_given() -> None:
    definitions = measure.contract()["definitions"]
    assert "at most 1.0 mm" in definitions["stance"] and measure.DEFINITIONS["stance_mm"] == 1.0
    assert "preceding 0.20 s" in definitions["speed"] and measure.DEFINITIONS["speed_window_s"] == 0.20
    assert "at least 0.10 s" in definitions["step"] and measure.DEFINITIONS["swing_min_s"] == 0.10
    assert "0.15 hip heights" in definitions["step"] and measure.DEFINITIONS["step_advance_hip_heights"] == 0.15
    reach_rows = {row["id"]: row for row in measure.contract()["behaviours"]["reach"]["predicates"]}
    assert "last 1.0 s" in reach_rows["Q2"]["metric"] and measure.REACH["final_window_s"] == 1.0
    assert "within 0.05 arm lengths" in reach_rows["Q3"]["metric"] and measure.REACH["tolerance_arm_lengths"] == 0.05


def test_the_reader_keeps_no_arithmetic_of_its_own() -> None:
    # One reader: the contract's runner binds predicates to the product's
    # metrics and measures nothing itself.
    source = (OT11 / "runner/measure.py").read_text(encoding="utf-8")
    for gone in ("import numpy", "import math", "import mujoco", "def gait(", "def foot_series(", "def base_series("):
        assert gone not in source, gone
    assert measure.evaluation.__name__.endswith("CadexEvaluation")


# -- the model and the report ----------------------------------------------

def test_the_rig_is_read_from_the_model_in_millimetres(tmp_path) -> None:
    pytest.importorskip("mujoco")
    path = tmp_path / "model.xml"
    path.write_text(fixtures.LEGGED_MODEL, encoding="utf-8")
    rig = measure.rig(path, ["foot"])
    assert rig["base"] == "base"
    # The hip, not the knee below it, and through the welded servo above it.
    assert rig["hip_height_mm"] == pytest.approx(100.0)
    assert rig["mass_kg"] == pytest.approx(0.5)
    assert rig["weight_n"] == pytest.approx(4.905)
    assert rig["com_height_mm"] == pytest.approx((0.4 * 100 + 0.05 * 60 + 0.05 * 10) / 0.5)
    (pad,) = rig["feet"]["foot"]
    assert pad["kind"] == "sphere" and pad["size_mm"][0] == pytest.approx(10.0)
    assert pad["pos_mm"] == pytest.approx([0.0, 0.0, -10.0])


def test_the_rig_of_an_arm_is_read_with_its_tip(tmp_path) -> None:
    pytest.importorskip("mujoco")
    path = tmp_path / "arm.xml"
    path.write_text(fixtures.ARM_MODEL, encoding="utf-8")
    rig = measure.rig(path, tip={"body": "hand", "local_mm": [0.0, 0.0, 10.0]})
    assert rig["base"] is None and rig["arm_length_mm"] == pytest.approx(220.0)
    with pytest.raises(SystemExit, match="no body of that name"):
        measure.rig(path, ["paw"])


def test_a_report_is_void_for_another_model_and_never_a_pass_off_contract(tmp_path) -> None:
    model = tmp_path / "model.xml"
    model.write_text("<mujoco/>", encoding="utf-8")
    frames = [{"frame_kind": "input", "nominal_time_s": None, "component_placements": {}}]
    frames += [{"frame_kind": "solver_output", "nominal_time_s": t, "component_placements": p}
               for t, p in trot()]
    trace = {"frames": frames, "dynamics": {"control_hz": 50, "steps_per_frame": 1},
             "policy": {"seed": 1101, "step_count": 500, "termination": "", "truncated": True,
                        "policy_sha256": "p", "model_sha256": measure.digest(model), "task_sha256": "t"}}
    path = tmp_path / "trace.json"
    path.write_text(json.dumps(trace), encoding="utf-8")
    good = measure.report("walk", path, model, walk_rig(), off_contract=False, command_mm_s=80.0)
    assert good["pass"] is True and good["void"] == [] and good["failing"] == []
    off = measure.report("walk", path, model, walk_rig(), off_contract=True, command_mm_s=80.0)
    assert off["pass"] is False and off["failing"] == []
    trace["policy"]["seed"] = 3
    trace["policy"]["model_sha256"] = "other"
    path.write_text(json.dumps(trace), encoding="utf-8")
    void = measure.report("walk", path, model, walk_rig(), off_contract=False, command_mm_s=80.0)
    assert void["pass"] is False and len(void["void"]) == 2
