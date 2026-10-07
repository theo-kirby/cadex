# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Every behaviour metric, on a rollout that passes it and one that fails it.

``CadexEvaluation`` (ADR-455) is what tells a walk from a shuffle, a reach
from a swing past the target, and a balance from a drive across the room.
Each metric is pinned here on a motion whose answer is stated
(``evaluation_fixtures``), and the gait family is pinned on the failure it
was written for: ot10's ``w2-2`` policy, which passed the old gait check.
"""

from __future__ import annotations

import ast
import json
import math
import sys
from pathlib import Path

import pytest

import CadexEvaluation as evaluation
from evaluation_fixtures import (
    ARM,
    ARM_MODEL,
    DONE,
    DT,
    IDENTITY,
    LEGGED_MODEL,
    RADIUS,
    SHOVES,
    TARGET_A,
    TARGET_B,
    W2_2,
    balance_rig,
    pitch,
    reach_rig,
    reaching,
    segments,
    shuffle,
    standing,
    trot,
    w2_2,
    walk_rig,
)

MODULE_DIR = Path(__file__).resolve().parents[1]

#: A walk spec, as the data a task will declare: a metric and its bounds.
WALK_SPEC = [
    {"id": "upright", "metric": "max_tilt_deg", "max": 30.0},
    {"id": "tracks_speed", "metric": "speed_ratio", "min": 0.75, "max": 1.25},
    {"id": "straight", "metric": "lateral_ratio", "max": 0.25},
    {"id": "heading", "metric": "max_heading_deg", "max": 45.0},
    {"id": "steps", "metric": "steps_min", "min": 4},
    {"id": "step_share", "metric": "step_share_min", "min": 0.70},
    {"id": "clearance", "metric": "step_clearance_hip_heights_min", "min": 0.08},
    {"id": "slip", "metric": "slip_share_max", "max": 0.15},
    {"id": "duty_low", "metric": "duty_factor_min", "min": 0.40},
    {"id": "duty_high", "metric": "duty_factor_max", "max": 0.85},
    {"id": "every_leg", "metric": "step_count_ratio", "max": 1.5},
    {"id": "on_the_floor", "metric": "foot_lowest_hip_heights_min", "min": -0.05},
]
REACH_SPEC = [
    {"id": "final_error", "metric": "final_error_arm_lengths_max", "max": 0.05},
    {"id": "time_to_target", "metric": "time_to_target_s_max", "max": 2.0},
    {"id": "overshoot", "metric": "overshoot_ratio_max", "max": 0.20},
]
BALANCE_SPEC = [
    {"id": "upright", "metric": "max_tilt_deg", "max": 30.0},
    {"id": "in_place", "metric": "max_drift_com_heights", "max": 2.0},
    {"id": "heading", "metric": "max_heading_deg", "max": 20.0},
    {"id": "recovers", "metric": "recovery_s_max", "max": 2.0},
]


def failing(spec, metrics):
    return [row["id"] for row in evaluation.check(spec, metrics) if not row["pass"]]


def walked(samples, command=80.0):
    return evaluation.gait_metrics(samples, walk_rig(), command)


# -- gait -------------------------------------------------------------------

def test_a_trot_with_real_steps_meets_a_walk_spec() -> None:
    metrics = walked(trot())
    assert failing(WALK_SPEC, metrics) == []
    assert 19 <= metrics["steps_min"] <= 21  # 10 s at 0.48 s a cycle
    assert metrics["step_count_ratio"] <= 1.06
    assert metrics["step_clearance_hip_heights_min"] == pytest.approx(0.15, abs=0.002)
    assert metrics["duty_factor_min"] == pytest.approx(0.5, abs=0.03)
    assert metrics["duty_factor_max"] == pytest.approx(0.5, abs=0.03)
    assert metrics["slip_share_max"] == pytest.approx(0.0, abs=1e-9)
    assert metrics["step_share_min"] > 0.95
    assert metrics["speed_ratio"] == pytest.approx(1.0, abs=0.01)
    assert metrics["mean_forward_speed_mm_s"] == pytest.approx(80.0, abs=0.5)
    assert metrics["lateral_ratio"] == pytest.approx(0.0, abs=1e-9)
    assert metrics["foot_lowest_hip_heights_min"] == pytest.approx(0.0, abs=1e-9)
    assert metrics["travel_mm"] == pytest.approx([800.0, 0.0])
    for foot in metrics["feet"].values():
        assert foot["median_step_clearance_mm"] == pytest.approx(15.0, abs=0.2)
        assert foot["median_step_advance_mm"] == pytest.approx(80.0 * 0.48, rel=0.01)
        assert foot["median_swing_airborne_s"] == pytest.approx(0.24)


def test_a_shuffle_takes_swings_and_no_steps() -> None:
    metrics = walked(shuffle(), 140.0)
    assert failing(WALK_SPEC, metrics) == ["steps", "step_share", "clearance", "slip", "every_leg"]
    assert metrics["steps_min"] == 0 and metrics["step_share_min"] == 0.0
    # No foot stepped, so there is no step to have a clearance or a ratio:
    # not measured, which a spec reads as failed rather than as zero.
    assert metrics["step_clearance_hip_heights_min"] is None
    assert metrics["step_count_ratio"] is None
    assert metrics["speed_ratio"] == pytest.approx(1.0, abs=0.01)  # it gets there, which is the trap
    for foot in metrics["feet"].values():
        assert foot["swings"] > 100 and foot["steps"] == 0
        assert foot["median_swing_peak_mm"] == pytest.approx(2.5)
        assert foot["median_swing_airborne_s"] == pytest.approx(0.04)


def test_feet_dragged_along_the_floor_are_all_slip_and_all_stance() -> None:
    metrics = walked(shuffle(hop=0.0), 140.0)
    assert metrics["slip_share_max"] == pytest.approx(1.0)
    assert metrics["duty_factor_min"] == 1.0 and metrics["duty_factor_max"] == 1.0
    assert {"slip", "duty_high"} <= set(failing(WALK_SPEC, metrics))


def test_steps_that_barely_clear_the_floor_fail_clearance_alone() -> None:
    metrics = walked(trot(lift=5.0))
    assert failing(WALK_SPEC, metrics) == ["clearance"]
    assert metrics["step_clearance_hip_heights_min"] == pytest.approx(0.05, abs=0.001)


def test_feet_driven_into_the_floor_fail_on_depth_alone() -> None:
    assert failing(WALK_SPEC, walked(trot(sink=4.0))) == []
    metrics = walked(trot(sink=6.0))
    assert failing(WALK_SPEC, metrics) == ["on_the_floor"]
    assert metrics["foot_lowest_hip_heights_min"] == pytest.approx(-0.06)
    assert all(foot["lowest_height_mm"] == pytest.approx(-6.0) for foot in metrics["feet"].values())


def test_a_landing_from_the_reset_lift_is_not_read_as_standing_in_the_floor() -> None:
    # ADR-467: a robot that holds its pose lands from the reset lift deeper
    # than it ever stands, so depth is read after the settle, like duty
    # factor and speed. The landing is still in the report.
    metrics = walked(trot(landing=10.0, sink=4.0))
    assert failing(WALK_SPEC, metrics) == []
    assert metrics["foot_lowest_hip_heights_min"] == pytest.approx(-0.04)
    for foot in metrics["feet"].values():
        assert foot["lowest_height_mm"] == pytest.approx(-10.0)
        assert foot["settled_lowest_height_mm"] == pytest.approx(-4.0)
    # ...and a foot that is still in the floor after the settle fails.
    assert failing(WALK_SPEC, walked(trot(landing=10.0, sink=6.0))) == ["on_the_floor"]


def test_the_wrong_speed_fails_tracking_alone() -> None:
    fast, slow = walked(trot(speed=80.0), 50.0), walked(trot(speed=80.0), 120.0)
    assert failing(WALK_SPEC, fast) == ["tracks_speed"] and fast["speed_ratio"] == pytest.approx(1.6, abs=0.01)
    assert failing(WALK_SPEC, slow) == ["tracks_speed"] and slow["speed_ratio"] == pytest.approx(0.667, abs=0.01)


def test_a_veer_is_a_heading_and_a_sideways_walk_is_a_lateral_speed() -> None:
    # The body turns while its feet keep carrying it along world X, so it is
    # off its heading and travelling across it.
    veer = walked(trot(heading=6.0))
    assert failing(WALK_SPEC, veer) == ["straight", "heading"]
    assert veer["max_heading_deg"] == pytest.approx(60.0) and veer["final_heading_deg"] == pytest.approx(60.0)
    crab = walked(trot(sideways=30.0))
    assert crab["lateral_ratio"] == pytest.approx(30.0 / 80.0, abs=0.01)
    assert crab["mean_lateral_speed_mm_s"] == pytest.approx(30.0, abs=0.5)
    assert "straight" in failing(WALK_SPEC, crab)


def test_a_heading_is_unwrapped_past_a_half_turn() -> None:
    assert walked(trot(heading=25.0))["max_heading_deg"] == pytest.approx(250.0)


def test_a_foot_that_mostly_hangs_in_the_air_fails_duty_factor() -> None:
    metrics = walked(trot(swing_frames=18))
    assert failing(WALK_SPEC, metrics) == ["duty_low"]
    assert metrics["duty_factor_min"] == pytest.approx(0.25, abs=0.02)


def test_a_tumble_is_a_tilt() -> None:
    samples = trot()
    samples[200][1]["base"]["rotation_xyzw"] = pitch(40.0)
    metrics = walked(samples)
    assert metrics["max_tilt_deg"] == pytest.approx(40.0) and "upright" in failing(WALK_SPEC, metrics)


def test_an_episode_that_ends_inside_the_settle_measures_no_speed_and_no_duty() -> None:
    metrics = walked(trot(seconds=0.84))
    assert metrics["speed_ratio"] is None and metrics["lateral_ratio"] is None
    assert metrics["duty_factor_min"] is None
    rows = {row["id"]: row for row in evaluation.check(WALK_SPEC, metrics)}
    assert rows["tracks_speed"]["pass"] is False and "not measured" in rows["tracks_speed"]["why"]
    json.dumps(metrics, allow_nan=False)  # no NaN reaches a report


def test_a_round_foot_rolling_through_its_stance_is_not_charged_as_slip() -> None:
    # A 7.5 mm ball rolling without slipping: its centre moves r * angle while
    # the material point on the floor does not move at all.
    geoms = walk_rig()["feet"]["fl"]
    samples = []
    for k in range(20):
        angle = 0.03 * k
        samples.append((k * DT, {"foot": {"position_mm": [RADIUS * angle, 0.0, RADIUS],
                                           "rotation_xyzw": pitch(math.degrees(angle))}}))
    rolling = evaluation.foot_series(samples, "foot", geoms, 0.0)
    assert sum(rolling["contact_travel"]) == pytest.approx(0.0, abs=0.02)
    assert math.dist(rolling["point"][-1], rolling["point"][0]) == pytest.approx(RADIUS * 0.57)
    sliding = [(t, {"foot": {**p["foot"], "rotation_xyzw": IDENTITY}}) for t, p in samples]
    assert sum(evaluation.foot_series(sliding, "foot", geoms, 0.0)["contact_travel"]) == pytest.approx(RADIUS * 0.57)


def test_a_foot_is_read_at_the_lowest_point_of_its_shape() -> None:
    box = {"kind": "box", "size_mm": [20.0, 10.0, 5.0], "pos_mm": [0.0, 0.0, 0.0], "quat_xyzw": IDENTITY}
    capsule = {"kind": "capsule", "size_mm": [4.0, 10.0, 0.0], "pos_mm": [0.0, 0.0, 0.0], "quat_xyzw": IDENTITY}
    flat = [(0.0, {"foot": {"position_mm": [0.0, 0.0, 30.0], "rotation_xyzw": IDENTITY}})]
    tipped = [(0.0, {"foot": {"position_mm": [0.0, 0.0, 30.0], "rotation_xyzw": pitch(30.0)}})]

    def height(samples, geoms, floor=0.0):
        return evaluation.foot_series(samples, "foot", geoms, floor)["height"][0]

    assert height(flat, [box]) == pytest.approx(25.0)
    expected = 30.0 - (20.0 * math.sin(math.radians(30.0)) + 5.0 * math.cos(math.radians(30.0)))
    assert height(tipped, [box]) == pytest.approx(expected)
    assert height(flat, [capsule]) == pytest.approx(16.0)
    # On its side the capsule is as low as its radius, not its half length.
    assert height([(0.0, {"foot": {"position_mm": [0.0, 0.0, 30.0], "rotation_xyzw": pitch(90.0)}})],
                  [capsule]) == pytest.approx(26.0)
    assert height(flat, [capsule, box]) == pytest.approx(16.0)  # the lowest of several
    assert height(flat, [box], floor=5.0) == pytest.approx(20.0)  # above the floor, not above zero


# -- the known negative -----------------------------------------------------

def test_the_w2_2_shuffle_fails_a_walk_spec_on_stepping_and_slip() -> None:
    samples, rig, command, episode = w2_2()
    assert len(samples) == 501 and episode["truncated"] and not episode["termination"]
    metrics = evaluation.gait_metrics(samples, rig, command)
    # It fails for the reason the owner gave -- it does not step and it
    # slides -- and not by accident on staying up, on heading or on clearance.
    assert failing(WALK_SPEC, metrics) == ["tracks_speed", "step_share", "slip", "every_leg", "on_the_floor"]
    feet = metrics["feet"]
    names = ["c_foot_fl", "c_foot_fr", "c_foot_rl", "c_foot_rr"]
    assert [feet[name]["swings"] for name in names] == [60, 66, 48, 61]
    assert [feet[name]["steps"] for name in names] == [18, 21, 5, 7]
    assert [feet[name]["step_share"] for name in names] == pytest.approx([0.359, 0.383, 0.141, 0.140], abs=0.001)
    assert [feet[name]["slip_share"] for name in names] == pytest.approx([0.324, 0.333, 0.666, 0.568], abs=0.001)
    assert [feet[name]["duty_factor"] for name in names] == pytest.approx([0.521, 0.508, 0.725, 0.690], abs=0.001)
    assert [feet[name]["lowest_height_mm"] for name in names] == pytest.approx([-17.58, -21.29, -8.36, -8.90], abs=0.01)
    # Read after the settle (ADR-467), every foot is still in the floor: only
    # the rear-left low was in the reset drop, and it stands at -8.08 later.
    assert [feet[name]["settled_lowest_height_mm"] for name in names] == pytest.approx([-17.58, -21.29, -8.08, -8.90], abs=0.01)
    # Chatter: the typical rear swing is two control steps long and 2.7 mm high.
    assert feet["c_foot_rl"]["median_swing_airborne_s"] == pytest.approx(0.04)
    assert feet["c_foot_rl"]["median_swing_peak_mm"] == pytest.approx(2.7, abs=0.1)
    assert metrics["step_share_min"] == pytest.approx(0.140, abs=0.001)
    assert metrics["slip_share_max"] == pytest.approx(0.666, abs=0.001)
    assert metrics["step_count_ratio"] == pytest.approx(4.2)
    assert metrics["speed_ratio"] == pytest.approx(1.907, abs=0.001)
    assert metrics["foot_lowest_hip_heights_min"] == pytest.approx(-0.2202, abs=0.0001)
    # What the old gait check read, and why it said yes.
    assert metrics["max_tilt_deg"] == pytest.approx(15.86, abs=0.01)
    assert metrics["max_heading_deg"] == pytest.approx(30.50, abs=0.01)
    assert metrics["step_clearance_hip_heights_min"] == pytest.approx(0.1006, abs=0.0001)


def test_the_w2_2_fixture_is_an_extract_and_not_the_rollout() -> None:
    fixture = json.loads(W2_2.read_text(encoding="utf-8"))
    assert fixture["bodies"] == ["c_tray", "c_foot_fl", "c_foot_fr", "c_foot_rl", "c_foot_rr"]
    assert all(len(row) == 35 for row in fixture["frames"])
    assert fixture["policy_sha256"].startswith("7a4e8c23") and fixture["mjcf_sha256"].startswith("49d11013")
    assert W2_2.stat().st_size < 200_000


# -- balance ----------------------------------------------------------------

def balanced(samples, shoves=SHOVES):
    return evaluation.balance_metrics(samples, balance_rig(), shoves)


def test_a_balancer_that_stays_put_and_recovers_meets_a_balance_spec() -> None:
    metrics = balanced(standing())
    assert failing(BALANCE_SPEC, metrics) == []
    assert metrics["max_tilt_deg"] == pytest.approx(8.0, abs=0.2)  # the second shove lands on the first's tail
    assert metrics["max_drift_mm"] == pytest.approx(20.0, abs=0.5)
    assert metrics["max_drift_com_heights"] == pytest.approx(0.4, abs=0.01)
    assert metrics["max_heading_deg"] == pytest.approx(0.0, abs=1e-6)
    assert metrics["shoves"] == 2 and all(0.0 <= t <= 2.0 for t in metrics["recovery_s"])
    assert metrics["recovery_s_max"] == max(metrics["recovery_s"])


def test_a_balancer_that_wanders_off_fails_staying_in_place() -> None:
    # Robin's ot9 shape: upright all episode, 105 mm/s in one direction.
    metrics = balanced(standing(drift=105.0, shoves=()), [])
    assert metrics["max_tilt_deg"] == pytest.approx(0.0, abs=1e-6)
    assert metrics["max_drift_mm"] == pytest.approx(1050.0, rel=0.01)
    assert metrics["final_drift_mm"] == metrics["max_drift_mm"]
    assert metrics["max_drift_com_heights"] == pytest.approx(21.0, rel=0.01)
    assert metrics["mean_speed_mm_s"] == pytest.approx(105.0, rel=0.01)
    # No shove was applied, so recovery was not measured -- and is not passed.
    assert metrics["shoves"] == 0 and metrics["recovery_s"] == [] and metrics["recovery_s_max"] is None
    assert failing(BALANCE_SPEC, metrics) == ["in_place", "recovers"]


def test_a_balancer_that_turns_fails_heading_alone() -> None:
    metrics = balanced(standing(turn=5.0))
    assert failing(BALANCE_SPEC, metrics) == ["heading"]
    assert metrics["max_heading_deg"] == pytest.approx(50.0, abs=0.01)
    assert metrics["final_heading_deg"] == pytest.approx(50.0, abs=0.01)


def test_a_shove_it_never_settles_from_has_no_recovery_time() -> None:
    slow = balanced(standing(settle=3.0, lean=25.0))
    assert "recovers" in failing(BALANCE_SPEC, slow)
    # Upright but never at rest: rolling at over one COM height (50 mm) a second.
    rolling = balanced(standing(drift=60.0, lean=2.0))
    assert rolling["recovery_s"] == [None, None] and rolling["recovery_s_max"] is None
    assert failing(BALANCE_SPEC, rolling) == ["in_place", "recovers"]


def test_a_fall_is_a_tilt() -> None:
    metrics = balanced(standing(lean=45.0))
    assert metrics["max_tilt_deg"] > 30.0 and "upright" in failing(BALANCE_SPEC, metrics)


def test_recovery_is_timed_from_the_shoves_end_to_the_start_of_a_full_second_of_rest() -> None:
    time = [k * DT for k in range(501)]
    tilt = [15.0 if 3.0 <= t < 3.8 else 1.0 for t in time]
    still = [0.0] * len(time)
    assert evaluation.recovery(time, tilt, still, 3.1, com_height_mm=50.0) == pytest.approx(0.7, abs=0.021)
    assert evaluation.recovery(time, tilt, still, 9.5, com_height_mm=50.0) is None  # no full second left
    # Rest is slow as well as upright, and a frame with no speed yet is not rest.
    rolling = [60.0 if t < 5.0 else 0.0 for t in time]
    assert evaluation.recovery(time, [1.0] * len(time), rolling, 3.1, com_height_mm=50.0) == pytest.approx(1.9, abs=0.021)
    assert evaluation.recovery(time, [1.0] * len(time), [None] * len(time), 3.1, com_height_mm=50.0) is None


# -- reach ------------------------------------------------------------------

def reached(samples, the_segments=None):
    return evaluation.reach_metrics(samples, reach_rig(), the_segments or segments())


def test_a_direct_reach_to_both_targets_meets_a_reach_spec() -> None:
    metrics = reached(reaching())
    assert failing(REACH_SPEC, metrics) == []
    assert metrics["targets"] == 2 and metrics["tolerance_mm"] == pytest.approx(10.0)
    first, second = metrics["segments"]
    assert first["start_distance_mm"] == pytest.approx(math.dist((150.0, 0.0, 100.0), TARGET_A))
    assert second["start_distance_mm"] == pytest.approx(math.dist(TARGET_A, TARGET_B))
    # A straight 1.0 s move is inside 10 mm once 1 - 10/length of it is done.
    assert first["time_to_target_s"] == pytest.approx(0.96, abs=1e-6)
    assert second["time_to_target_s"] == pytest.approx(0.92, abs=1e-6)
    assert metrics["time_to_target_s_max"] == pytest.approx(0.96, abs=1e-6)
    assert metrics["final_error_mm_max"] == pytest.approx(0.0, abs=1e-6)
    assert metrics["overshoot_ratio_max"] == pytest.approx(0.0, abs=1e-9)


def test_a_swing_past_the_target_is_an_overshoot() -> None:
    metrics = reached(reaching(over=0.3))
    assert failing(REACH_SPEC, metrics) == ["overshoot"]
    assert [row["overshoot_ratio"] for row in metrics["segments"]] == pytest.approx([0.3, 0.3])
    # ...and it has not arrived until it has come back and stayed.
    assert metrics["segments"][0]["time_to_target_s"] == pytest.approx(1.38, abs=1e-6)
    assert metrics["final_error_mm_max"] == pytest.approx(0.0, abs=1e-6)


def test_a_slow_reach_fails_time_alone() -> None:
    metrics = reached(reaching(move_s=3.0))
    assert failing(REACH_SPEC, metrics) == ["time_to_target"]
    assert metrics["time_to_target_s_max"] == pytest.approx(3.0 * (1 - 10.0 / math.dist((150.0, 0.0, 100.0), TARGET_A)),
                                                          abs=DT)


def test_a_reach_that_stops_short_never_arrives() -> None:
    metrics = reached(reaching(miss_mm=20.0))
    assert failing(REACH_SPEC, metrics) == ["final_error", "time_to_target"]
    assert metrics["final_error_mm_max"] == pytest.approx(20.0)
    assert metrics["final_error_arm_lengths_max"] == pytest.approx(20.0 / ARM)
    assert [row["time_to_target_s"] for row in metrics["segments"]] == [None, None]
    assert metrics["time_to_target_s_max"] is None
    assert [row["closest_mm"] for row in metrics["segments"]] == pytest.approx([20.0, 20.0])


def test_a_tip_that_arrives_and_then_leaves_has_not_reached() -> None:
    metrics = reached(reaching(leaves_at=7.0))
    first, second = metrics["segments"]
    assert first["time_to_target_s"] == pytest.approx(0.96, abs=1e-6)
    assert second["time_to_target_s"] is None and second["closest_mm"] == pytest.approx(0.0, abs=1e-6)
    # The final error is the worst of the last second, not the last frame's luck.
    assert second["final_error_mm"] == pytest.approx(50.0)
    assert failing(REACH_SPEC, metrics) == ["final_error", "time_to_target"]


def test_the_frame_on_a_target_switch_belongs_to_the_new_target() -> None:
    metrics = reached(reaching())
    first, second = metrics["segments"]
    assert first["frames"] == 200 and second["frames"] == 201  # 0.00-3.98 s, then 4.00-8.00 s
    # Were the switch frame charged to target A, A's tip would be at A there
    # and B's move would start one frame late.
    assert second["start_distance_mm"] == pytest.approx(math.dist(TARGET_A, TARGET_B))


def test_the_tip_is_a_point_on_the_hand_and_not_the_hands_origin() -> None:
    for hand_yaw in (0.0, 90.0, 210.0):
        metrics = reached(reaching(hand_yaw=hand_yaw))
        assert metrics["final_error_mm_max"] == pytest.approx(0.0, abs=1e-6)
    origin = dict(reach_rig(), tip={"body": "hand", "local_mm": [0.0, 0.0, 0.0]})
    wrong = evaluation.reach_metrics(reaching(), origin, segments())
    assert wrong["final_error_mm_max"] == pytest.approx(40.0)


def test_a_target_with_no_frames_is_not_measured() -> None:
    late = [{"start_s": 0.0, "end_s": 8.0, "target_mm": list(TARGET_A)},
            {"start_s": 20.0, "end_s": 24.0, "target_mm": list(TARGET_B)}]
    metrics = reached(reaching(switch=100.0), late)
    assert metrics["segments"][1]["frames"] == 0 and metrics["final_error_mm_max"] is None
    assert failing(REACH_SPEC, metrics) == ["final_error", "time_to_target", "overshoot"]


def test_an_episode_that_ends_before_the_final_window_is_not_measured() -> None:
    # Terminated at 6 s of an 8 s target: no frame in the last second.
    metrics = reached(reaching(seconds=6.0))
    second = metrics["segments"][1]
    assert second["frames"] > 0 and second["final_error_mm"] is None
    assert metrics["final_error_mm_max"] is None and "final_error" in failing(REACH_SPEC, metrics)


# -- the episode, and a spec ------------------------------------------------

def test_completed_means_the_horizon_was_reached_and_nothing_fired() -> None:
    assert evaluation.episode_metrics(DONE) == {"completed": 1.0, "duration_s": 10.0, "termination": ""}
    tipped = {**DONE, "termination": "tipped", "truncated": False, "duration_s": 4.0}
    assert evaluation.episode_metrics(tipped)["completed"] == 0.0
    assert evaluation.episode_metrics({**DONE, "truncated": False})["completed"] == 0.0
    assert failing([{"id": "completes", "metric": "completed", "min": 1}], evaluation.episode_metrics(tipped)) == ["completes"]


def test_a_predicate_is_a_metric_and_its_bounds_and_the_bounds_are_inclusive() -> None:
    spec = [{"id": "a", "metric": "x", "min": 1.0, "max": 2.0}]
    assert [evaluation.check(spec, {"x": x})[0]["pass"] for x in (0.99, 1.0, 1.5, 2.0, 2.01)] == [
        False, True, True, True, False]
    low = evaluation.check(spec, {"x": 0.5})[0]
    assert low == {"id": "a", "metric": "x", "value": 0.5, "min": 1.0, "max": 2.0, "pass": False,
                   "why": "x is 0.5, under 1"}
    assert evaluation.check(spec, {"x": 3})[0]["why"] == "x is 3, over 2"
    assert evaluation.check([{"metric": "x", "max": 2}], {"x": 1})[0]["id"] == "x"


def test_a_metric_nobody_measured_fails_and_says_so() -> None:
    spec = [{"id": "a", "metric": "x", "max": 2.0}]
    for metrics in ({}, {"x": None}, {"x": float("nan")}, {"x": float("-inf")}, {"x": True},
                    {"x": "1.0"}, {"x": [1.0]}):
        (row,) = evaluation.check(spec, metrics)
        assert row["pass"] is False and row["value"] is None and row["why"] == "x was not measured"
    with pytest.raises(ValueError, match="states no bound"):
        evaluation.check([{"id": "a", "metric": "x"}], {"x": 1.0})


def test_the_vocabulary_is_exactly_what_the_families_measure() -> None:
    """A success spec names a metric from ``METRICS`` (ADR-456), so every
    name there is one a family really returns as a number -- and the three
    spec fixtures above are written in it."""

    measured = {
        "episode": evaluation.episode_metrics(DONE),
        "posture": balanced(standing()),
        "gait": walked(trot()),
        "reach": reached(reaching()),
    }
    for name, (family, needs) in evaluation.METRICS.items():
        value = measured[family][name]
        assert isinstance(value, (int, float)) and not isinstance(value, bool), name
        assert set(needs) <= {"base", "floor", "feet", "tip", "shove", "command", "target"}, name
    for spec in (WALK_SPEC, REACH_SPEC, BALANCE_SPEC):
        assert {row["metric"] for row in spec} <= set(evaluation.METRICS)
    # What needs a goal is what is a ratio of, or a distance from, one: a
    # commanded speed for the two ratios, a target point for the reach.
    assert {name for name, (_, needs) in evaluation.METRICS.items() if "command" in needs} == {
        "speed_ratio", "lateral_ratio"}
    assert {name for name, (_, needs) in evaluation.METRICS.items() if "target" in needs} == {
        "final_error_mm_max", "final_error_arm_lengths_max",
        "time_to_target_s_max", "overshoot_ratio_max"}
    assert not [name for name in evaluation.METRICS if "reward" in name]


# -- one rollout as one table, and a set of seeds together (ADR-457) ----------

def test_measure_reads_the_families_the_rig_has_and_no_others() -> None:
    """The table is what a predicate may bound: ``METRICS`` names, nothing else."""

    posture = {name for name, (family, _) in evaluation.METRICS.items() if family == "posture"}
    gait = {name for name, (family, _) in evaluation.METRICS.items() if family == "gait"}
    reach = {name for name, (family, _) in evaluation.METRICS.items() if family == "reach"}

    standing_still = evaluation.measure(standing(), DONE, balance_rig(), shoves=SHOVES)
    assert set(standing_still["metrics"]) == {"completed", "duration_s"} | posture
    assert standing_still["metrics"] == {
        name: value for name, value in {**evaluation.episode_metrics(DONE),
                                        **balanced(standing())}.items()
        if name in evaluation.METRICS}
    assert standing_still["detail"] == {"recovery_s": balanced(standing())["recovery_s"]}

    walking = evaluation.measure(trot(), DONE, walk_rig(), command_mm_s=80.0)
    assert set(walking["metrics"]) == {"completed", "duration_s"} | posture | gait
    assert walking["metrics"]["speed_ratio"] == walked(trot())["speed_ratio"]
    assert sorted(walking["detail"]["feet"]) == sorted(walk_rig()["feet"])
    # No shove was applied, so there is no recovery: measured as nothing.
    assert walking["metrics"]["recovery_s_max"] is None and walking["detail"]["recovery_s"] == []

    arm = evaluation.measure(reaching(), {**DONE, "duration_s": 8.0}, reach_rig(),
                             segments=segments())
    assert set(arm["metrics"]) == {"completed", "duration_s"} | reach
    assert len(arm["detail"]["segments"]) == 2
    # An arm with no target stated has only how its episode ended.
    assert set(evaluation.measure(reaching(), DONE, reach_rig())["metrics"]) == {
        "completed", "duration_s"}


def test_a_base_with_no_floor_under_it_has_no_drift_in_com_heights() -> None:
    rig = {**balance_rig(), "com_height_mm": None, "floor_mm": None}
    metrics = evaluation.measure(standing(drift=105.0, shoves=()), DONE, rig)["metrics"]
    assert metrics["max_drift_com_heights"] is None
    assert metrics["max_drift_mm"] == pytest.approx(1050.0, rel=0.01)
    assert "recovery_s_max" not in metrics


def test_the_w2_2_shuffle_fails_stepping_and_slip_through_the_one_table() -> None:
    """The known negative, read the way the evaluation command reads a seed."""

    samples, rig, _command, episode = w2_2()
    spec = [row for row in WALK_SPEC if "ratio" not in row["metric"] or row["id"] == "every_leg"]
    measured = evaluation.measure(samples, episode, rig)
    held = evaluation.check(spec, measured["metrics"])
    assert [row["id"] for row in held if not row["pass"]] == [
        "step_share", "slip", "every_leg", "on_the_floor"]
    assert measured["metrics"]["completed"] == 1.0
    assert measured["metrics"]["speed_ratio"] is None  # no goal was stated


def _seed(seed, spec, metrics, *, termination="", reward=(1.0, 2.0)):
    held = evaluation.check(spec, metrics)
    return {"seed": seed, "pass": all(row["pass"] for row in held), "predicates": held,
            "metrics": metrics, "episode": {"termination": termination},
            "reward": {"total": sum(reward), "terms": [{"label": "alive", "total": reward[0]},
                                                       {"label": "speed", "total": reward[1]}]}}


def test_a_summary_counts_seeds_and_never_averages_a_verdict() -> None:
    spec = [{"id": "upright", "metric": "max_tilt_deg", "max": 30.0},
            {"id": "recovers", "metric": "recovery_s_max", "max": 2.0}]
    seeds = [
        _seed(1101, spec, {"max_tilt_deg": 5.0, "recovery_s_max": 0.5}),
        _seed(1102, spec, {"max_tilt_deg": 10.0, "recovery_s_max": 1.0}, reward=(3.0, 4.0)),
        _seed(1103, spec, {"max_tilt_deg": 90.0, "recovery_s_max": None},
              termination="fallen", reward=(0.5, 0.0)),
    ]
    summary = evaluation.summarise(seeds, spec)

    assert summary["seeds"] == 3 and summary["passed"] == [1101, 1102]
    assert summary["failed"] == [1103] and summary["pass"] is False
    upright, recovers = summary["predicates"]
    # The mean tilt is 35 and the median 10: neither is what decided this.
    assert upright == {"id": "upright", "metric": "max_tilt_deg", "min": None, "max": 30.0,
                       "passed": 2, "failed_seeds": [1103],
                       "value": {"min": 5.0, "median": 10.0, "max": 90.0}}
    assert recovers["failed_seeds"] == [1103]
    assert recovers["value"] == {"min": 0.5, "median": 0.75, "max": 1.0}
    assert summary["terminations"] == {"horizon": 2, "fallen": 1}
    assert summary["metrics"]["recovery_s_max"] == {"measured": 2, "min": 0.5, "median": 0.75,
                                                    "max": 1.0}
    assert summary["metrics"]["max_tilt_deg"]["measured"] == 3
    assert summary["reward"]["total"] == {"min": 0.5, "median": 3.0, "max": 7.0}
    assert summary["reward"]["terms"] == [
        {"label": "alive", "min": 0.5, "median": 1.0, "max": 3.0},
        {"label": "speed", "min": 0.0, "median": 2.0, "max": 4.0}]

    assert evaluation.summarise(seeds[:2], spec)["pass"] is True
    # No seed is no evidence, and no evidence is not a pass.
    empty = evaluation.summarise([], spec)
    assert empty["pass"] is False and empty["seeds"] == 0
    assert [row["id"] for row in empty["predicates"]] == ["upright", "recovers"]


def test_a_gait_with_no_commanded_speed_is_still_measured_and_tracks_nothing() -> None:
    commanded, free = walked(trot()), evaluation.gait_metrics(trot(), walk_rig())
    assert free["command_mm_s"] is None
    assert free["speed_ratio"] is None and free["lateral_ratio"] is None
    assert failing([{"id": "tracks", "metric": "speed_ratio", "min": 0.75}], free) == ["tracks"]
    for name, value in commanded.items():
        if name not in ("command_mm_s", "speed_ratio", "lateral_ratio"):
            assert free[name] == value, name
    assert free["mean_forward_speed_mm_s"] == pytest.approx(80.0, rel=0.02)


def test_a_trace_is_read_as_its_timed_frames_its_episode_and_its_digests(tmp_path) -> None:
    frames = [{"frame_kind": "input", "nominal_time_s": None, "component_placements": {}}]
    frames += [{"frame_kind": "solver_output", "nominal_time_s": t, "component_placements": p} for t, p in trot()]
    raw = {"frames": frames, "dynamics": {"control_hz": 50, "steps_per_frame": 1},
           "policy": {"seed": 1101, "step_count": 500, "termination": "", "truncated": True,
                      "policy_sha256": "p", "model_sha256": "m", "task_sha256": "t"}}
    path = tmp_path / "trace.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    trace = evaluation.load_trace(path)
    assert len(trace["samples"]) == 501 and trace["samples"][0][0] == 0.0
    assert trace["episode"] == {"seed": 1101, "steps": 500, "control_hz": 50, "steps_per_frame": 1,
                                "duration_s": 10.0, "termination": "", "truncated": True}
    assert trace["digests"] == {"policy_sha256": "p", "mjcf_sha256": "m", "task_sha256": "t"}
    assert failing(WALK_SPEC, evaluation.gait_metrics(trace["samples"], walk_rig(), 80.0)) == []


# -- the model's half -------------------------------------------------------

def _model(xml: str):
    pytest.importorskip("mujoco")
    import CadexDynamics

    return CadexDynamics, CadexDynamics.load_model(xml.encode("utf-8"))


def test_the_rig_is_read_from_the_model_in_millimetres() -> None:
    dynamics, model = _model(LEGGED_MODEL)
    rig = dynamics.evaluation_rig(model, feet=["foot"])
    assert rig["base"] == "base" and rig["floor_mm"] == 0.0
    assert rig["reference_xyzw"] == pytest.approx(IDENTITY)
    # The hip, not the knee below it, and through the welded servo above it.
    assert rig["hip_height_mm"] == pytest.approx(100.0)
    assert rig["mass_kg"] == pytest.approx(0.5)
    assert rig["weight_n"] == pytest.approx(4.905)
    assert rig["com_height_mm"] == pytest.approx((0.4 * 100 + 0.05 * 60 + 0.05 * 10) / 0.5)
    (pad,) = rig["feet"]["foot"]
    assert pad["kind"] == "sphere" and pad["size_mm"][0] == pytest.approx(10.0)
    assert pad["pos_mm"] == pytest.approx([0.0, 0.0, -10.0])
    assert "tip" not in rig
    json.dumps(rig, allow_nan=False)


def test_a_grounded_arm_has_no_base_and_an_arm_length_from_its_first_driven_joint() -> None:
    dynamics, model = _model(ARM_MODEL)
    rig = dynamics.evaluation_rig(model, tip={"body": "hand", "local_mm": [0.0, 0.0, 10.0]})
    assert rig["base"] is None and rig["feet"] == {} and rig["hip_height_mm"] is None
    # Shoulder to elbow is 120 mm, elbow to the tip is 90 + 10: the undriven
    # turntable under the shoulder is not part of the arm.
    assert rig["arm_length_mm"] == pytest.approx(220.0)
    assert rig["tip"]["solved_mm"] == pytest.approx([120.0, 0.0, 200.0])
    assert rig["mass_kg"] == pytest.approx(0.45)
    assert dynamics.evaluation_rig(model, tip={"body": "hand"})["arm_length_mm"] == pytest.approx(210.0)


def test_a_foots_height_from_the_trace_is_the_physics_engines_own() -> None:
    dynamics, model = _model(LEGGED_MODEL)
    import mujoco

    rig = dynamics.evaluation_rig(model, feet=["foot"])
    data = mujoco.MjData(model)
    samples, expected = [], []
    data.qvel[3:6] = [0.4, 1.1, -0.3]  # tumbling as it falls, so the pose matters
    pad = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "pad")
    for step in range(40):
        mujoco.mj_step(model, data)
        placements = {}
        for name in ("base", "foot"):
            body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
            placements[name] = {
                "position_mm": dynamics.vector_mm(data.xpos[body]),
                "rotation_xyzw": dynamics.quaternion_xyzw_from_wxyz(data.xquat[body]),
            }
        samples.append((step * model.opt.timestep, placements))
        expected.append(dynamics.length_mm(data.geom_xpos[pad][2]) - 10.0)
    series = evaluation.foot_series(samples, "foot", rig["feet"]["foot"], rig["floor_mm"])
    assert series["height"] == pytest.approx(expected, abs=1e-6)
    base = evaluation.base_series(samples, rig)
    assert base["tilt"][-1] > 1.0  # it did tumble


@pytest.mark.parametrize(
    ("xml", "arguments", "reason"),
    [
        (LEGGED_MODEL, {"feet": ["paw"]}, "evaluation_body_missing"),
        (LEGGED_MODEL, {"feet": ["servo"]}, "evaluation_foot_has_no_geom"),
        (LEGGED_MODEL, {"feet": ["base"]}, "evaluation_foot_has_no_geom"),
        (LEGGED_MODEL, {"tip": {"body": "foot"}}, "evaluation_tip_is_not_driven"),
        (LEGGED_MODEL.replace('name="solved"', 'name="other"'), {}, "evaluation_keyframe_missing"),
        (LEGGED_MODEL.replace('type="sphere" size="0.01"', 'type="cylinder" size="0.01 0.01"'),
         {"feet": ["foot"]}, "evaluation_foot_geom_unsupported"),
        (LEGGED_MODEL.replace("</worldbody>", '<body name="ball" pos="1 0 1"><freejoint/>'
                              '<geom type="sphere" size="0.01"/></body></worldbody>'),
         {}, "evaluation_base_ambiguous"),
        (ARM_MODEL, {"feet": ["hand"]}, "evaluation_feet_need_a_floor"),
        (ARM_MODEL, {"tip": {"body": "hand", "local_mm": [0.0, 1.0]}}, "malformed_frame"),
    ],
)
def test_a_rig_that_cannot_be_read_is_refused_by_name(xml, arguments, reason) -> None:
    dynamics, model = _model(xml)
    with pytest.raises(dynamics.DynamicsError) as refusal:
        dynamics.evaluation_rig(model, **arguments)
    assert refusal.value.reason == reason


# -- where it lives ---------------------------------------------------------

def test_the_metrics_module_is_standard_library_and_outside_the_service() -> None:
    from test_engine_purity_guardrails import _engine_closure, _import_roots

    roots = _import_roots(MODULE_DIR / "CadexEvaluation.py")
    assert roots <= set(sys.stdlib_module_names), roots - set(sys.stdlib_module_names)
    # A client loads it by path with no engine built (CadexStudio's standing),
    # and cadexd never imports it.
    assert "CadexEvaluation" not in _engine_closure()
    assert "    CadexEvaluation.py\n" in (MODULE_DIR / "CMakeLists.txt").read_text(encoding="utf-8")
    # It reads millimetres and degrees and converts nothing; the model's
    # metres are converted where every other one is.
    from test_dynamics_units import _NO_CONVERSION_MODULES

    assert "CadexEvaluation.py" in _NO_CONVERSION_MODULES
    tree = ast.parse((MODULE_DIR / "CadexDynamics.py").read_text(encoding="utf-8"))
    assert any(isinstance(node, ast.FunctionDef) and node.name == "evaluation_rig" for node in tree.body)
