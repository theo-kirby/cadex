# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The ot11 contract reader, on gaits and balances whose answers are stated.

``docs/probes/ot11/runner/measure.py`` is what measured the known negatives
(ot10's ``w2-2`` shuffle, ot9's Robin) against the frozen walk and balance
specs. A reader that fails everything proves nothing about a shuffle, so
each predicate is pinned here on a synthetic trace that passes it and one
that fails it for the stated reason.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
OT11 = REPO / "docs/probes/ot11"

_spec = importlib.util.spec_from_file_location("ot11_measure", OT11 / "runner/measure.py")
measure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(measure)

IDENTITY = [0.0, 0.0, 0.0, 1.0]
HIP = 100.0
FEET = {"fl": (60.0, 40.0), "fr": (60.0, -40.0), "rl": (-60.0, 40.0), "rr": (-60.0, -40.0)}
RADIUS = 7.5
DT = 0.02
DONE = {"duration_s": 10.0, "termination": "", "truncated": True, "seed": 1101}


def walk_rig():
    sphere = {"kind": "sphere", "size_mm": [RADIUS, 0.0, 0.0], "pos_mm": [0.0, 0.0, 0.0], "quat_xyzw": IDENTITY}
    return {"base": "base", "reference_xyzw": IDENTITY, "base_com_local_mm": [0.0, 0.0, 0.0],
            "floor_mm": 0.0, "hip_height_mm": HIP, "com_height_mm": 80.0,
            "feet": {name: [sphere] for name in FEET}}


def yaw(degrees: float) -> list[float]:
    half = math.radians(degrees) / 2.0
    return [0.0, 0.0, math.sin(half), math.cos(half)]


def pitch(degrees: float) -> list[float]:
    half = math.radians(degrees) / 2.0
    return [0.0, math.sin(half), 0.0, math.cos(half)]


def trot(*, speed=80.0, lift=15.0, period_frames=24, seconds=10.0, swing_frames=None,
         heading=0.0, sideways=0.0, sink=0.0):
    """A trot: diagonal pairs swing in turn, stance feet stay where they landed."""

    swing_frames = period_frames // 2 if swing_frames is None else swing_frames
    samples = []
    for k in range(int(round(seconds / DT)) + 1):
        t = k * DT
        placements = {"base": {"position_mm": [speed * t, sideways * t, 90.0], "rotation_xyzw": yaw(heading * t)}}
        for name, (x, y) in FEET.items():
            shift = 0 if name in ("fl", "rr") else period_frames // 2
            cycle, phase = divmod(k + shift, period_frames)
            stride = speed * period_frames * DT
            if phase < swing_frames:
                fraction = (phase + 0.5) / swing_frames
                along = (cycle - 1) * stride + stride * fraction
                height = lift * math.sin(math.pi * fraction)
            else:
                along, height = cycle * stride, -sink
            placements[name] = {"position_mm": [x + along, y, RADIUS + height], "rotation_xyzw": IDENTITY}
        samples.append((t, placements))
    return samples


def shuffle(*, speed=140.0, hop=2.5, seconds=10.0):
    """The w2-2 shape: feet chatter forward in 40 ms hops a few millimetres high."""

    samples = []
    for k in range(int(round(seconds / DT)) + 1):
        t = k * DT
        placements = {"base": {"position_mm": [speed * t, 0.0, 90.0], "rotation_xyzw": IDENTITY}}
        for name, (x, y) in FEET.items():
            airborne = (k + (0 if name in ("fl", "rr") else 2)) % 4 < 2
            placements[name] = {"position_mm": [x + speed * t, y, RADIUS + (hop if airborne else 0.0)],
                                "rotation_xyzw": IDENTITY}
        samples.append((t, placements))
    return samples


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


def test_a_round_foot_rolling_through_its_stance_is_not_charged_as_slip() -> None:
    # A 7.5 mm ball rolling without slipping: its centre moves r * angle while
    # the material point on the floor does not move at all.
    geoms = {"name": "foot", "geoms": walk_rig()["feet"]["fl"]}
    samples = []
    for k in range(20):
        angle = 0.03 * k
        samples.append((k * DT, {"foot": {"position_mm": [RADIUS * angle, 0.0, RADIUS],
                                           "rotation_xyzw": pitch(math.degrees(angle))}}))
    rolling = measure.foot_series(samples, geoms, 0.0)
    assert rolling["contact_travel"].sum() == pytest.approx(0.0, abs=0.02)
    assert np.linalg.norm(rolling["point"][-1] - rolling["point"][0]) == pytest.approx(RADIUS * 0.57)
    sliding = [(t, {"foot": {**p["foot"], "rotation_xyzw": IDENTITY}}) for t, p in samples]
    assert measure.foot_series(sliding, geoms, 0.0)["contact_travel"].sum() == pytest.approx(RADIUS * 0.57)


def test_a_box_foot_is_read_at_its_lowest_corner() -> None:
    box = {"kind": "box", "size_mm": [20.0, 10.0, 5.0], "pos_mm": [0.0, 0.0, 0.0], "quat_xyzw": IDENTITY}
    capsule = {"kind": "capsule", "size_mm": [4.0, 10.0, 0.0], "pos_mm": [0.0, 0.0, 0.0], "quat_xyzw": IDENTITY}
    flat = [(0.0, {"foot": {"position_mm": [0.0, 0.0, 30.0], "rotation_xyzw": IDENTITY}})]
    tipped = [(0.0, {"foot": {"position_mm": [0.0, 0.0, 30.0], "rotation_xyzw": pitch(30.0)}})]
    assert measure.foot_series(flat, {"name": "foot", "geoms": [box]}, 0.0)["height"][0] == pytest.approx(25.0)
    expected = 30.0 - (20.0 * math.sin(math.radians(30.0)) + 5.0 * math.cos(math.radians(30.0)))
    assert measure.foot_series(tipped, {"name": "foot", "geoms": [box]}, 0.0)["height"][0] == pytest.approx(expected)
    assert measure.foot_series(flat, {"name": "foot", "geoms": [capsule]}, 0.0)["height"][0] == pytest.approx(16.0)


# -- balance ----------------------------------------------------------------

def balance_rig():
    return {"base": "base", "reference_xyzw": IDENTITY, "base_com_local_mm": [0.0, 0.0, 0.0],
            "floor_mm": 0.0, "com_height_mm": 50.0, "hip_height_mm": None, "feet": {}}


def standing(*, drift=0.0, turn=0.0, shoves=((2.5, 0.1), (6.0, 0.1)), bump=20.0, lean=8.0, settle=0.6,
             seconds=10.0):
    """A balancer that is knocked ``bump`` mm and ``lean`` degrees by each
    shove and settles back with time constant ``settle``; plus a steady
    ``drift`` (mm/s) and ``turn`` (deg/s)."""

    samples = []
    for k in range(int(round(seconds / DT)) + 1):
        t = k * DT
        x, tilt = drift * t, 0.0
        for onset, duration in shoves:
            since = t - onset
            if since >= 0.0:
                pulse = (since / settle) * math.exp(1.0 - since / settle)
                x += bump * pulse
                tilt += lean * pulse
        half_yaw, half_tilt = math.radians(turn * t) / 2.0, math.radians(tilt) / 2.0
        # yaw about world Z after a pitch: q = q_yaw * q_pitch
        rotation = [-math.sin(half_yaw) * math.sin(half_tilt), math.cos(half_yaw) * math.sin(half_tilt),
                    math.sin(half_yaw) * math.cos(half_tilt), math.cos(half_yaw) * math.cos(half_tilt)]
        samples.append((t, {"base": {"position_mm": [x, 0.0, 50.0], "rotation_xyzw": rotation}}))
    return samples


SHOVES = [(2.5, 0.1), (6.0, 0.1)]


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


def test_recovery_is_timed_from_the_shoves_end_to_the_start_of_a_full_second_of_rest() -> None:
    time = np.arange(0.0, 10.0 + 1e-9, DT)
    tilt = np.where((time >= 3.0) & (time < 3.8), 15.0, 1.0)
    speed = np.zeros_like(time)
    rest = measure.predicate("balance", "B5")["rest"]
    assert measure.recovery(time, tilt, speed, 3.1, rest, 50.0) == pytest.approx(0.7, abs=0.021)
    assert measure.recovery(time, tilt, speed, 9.5, rest, 50.0) is None  # no full second left to rest in


# -- the model and the report ----------------------------------------------

MODEL = """<mujoco>
  <worldbody>
    <geom name="floor" type="plane" size="0 0 0.05"/>
    <body name="base" pos="0 0 0.1">
      <freejoint/>
      <geom type="box" size="0.05 0.03 0.01" mass="0.4" contype="0" conaffinity="0"/>
      <body name="servo" pos="0.04 0 0.02">
        <body name="leg" pos="0 0 -0.02">
          <joint name="hip" type="hinge" axis="0 1 0"/>
          <geom type="capsule" fromto="0 0 0 0 0 -0.08" size="0.004" mass="0.05" contype="0" conaffinity="0"/>
          <body name="shin" pos="0 0 -0.04">
            <joint name="knee" type="hinge" axis="0 1 0"/>
            <body name="foot" pos="0 0 -0.04">
              <geom name="pad" type="sphere" size="0.01" pos="0 0 -0.01" mass="0.05"/>
            </body>
          </body>
        </body>
      </body>
    </body>
  </worldbody>
  <keyframe><key name="solved"/></keyframe>
</mujoco>
"""


def test_the_rig_is_read_from_the_model_in_millimetres(tmp_path) -> None:
    pytest.importorskip("mujoco")
    path = tmp_path / "model.xml"
    path.write_text(MODEL, encoding="utf-8")
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
