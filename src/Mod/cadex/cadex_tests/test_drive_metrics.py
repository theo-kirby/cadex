# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The drive family: smoothness, clamp load and cost of transport (ADR-704).

Each metric is pinned on drive signals whose answer is stated -- a sinusoid
has a known rate and acceleration RMS, a stride with jitter on it a known
share of power above three times its frequency -- written as the frames a
rollout trace carries since ADR-694, with no physics.
"""

from __future__ import annotations

import math

import pytest

import CadexEvaluation as evaluation
from evaluation_fixtures import DONE, DT, trot, walk_rig
from evaluation_fixtures import drive_channel as channel
from evaluation_fixtures import drive_frames as frames

SECONDS = 10.0


def sine(amplitude: float, hertz: float, t: float) -> float:
    return amplitude * math.sin(2.0 * math.pi * hertz * t)


def test_a_trace_without_joint_state_has_no_drive_series() -> None:
    old = [{"frame_kind": "solver_output", "nominal_time_s": 0.0, "component_placements": {},
            "actuator_commands": [0.0]}]
    assert evaluation.drive_series(old, [channel("a")]) is None
    assert evaluation.drive_series(frames(lambda t: ([0.0], [0.0], [0.0], [0.0])), []) is None
    series = evaluation.drive_series(frames(lambda t: ([1.0], [2.0], [3.0], [4.0])), [channel("a")])
    assert series["commands"][0] is None and series["efforts"][0] is None
    assert series["commands"][1] == [3.0] and series["positions"][0] == [1.0]
    assert len(series["time"]) == int(round(SECONDS / DT)) + 1


def test_command_rate_is_pooled_in_channel_ranges_per_second() -> None:
    # A position drive over a 180-degree range and a torque drive over
    # 2,000 N·mm, each swinging a quarter of its range at 1.5 Hz.
    hz, ranges = 1.5, (180.0, 2000.0)

    def signals(t):
        return [0.0, 0.0], [0.0, 0.0], [sine(r / 4.0, hz, t) for r in ranges], [0.0, 0.0]

    series = evaluation.drive_series(frames(signals), [
        channel("pos"), channel("torque", low=-1000.0, high=1000.0)])
    read = evaluation.drive_metrics(series)
    # d/dt of (1/4) sin(2 pi f t) has RMS (1/4) 2 pi f / sqrt 2, for both.
    expected = 0.25 * 2.0 * math.pi * hz / math.sqrt(2.0)
    assert read["command_rate_rms"] == pytest.approx(expected, rel=0.02)
    rows = read["drives"]["channels"]
    assert rows[0]["command_rate_rms"] == pytest.approx(rows[1]["command_rate_rms"], rel=1e-9)


def test_joint_acceleration_is_read_on_angular_joints_after_the_settle() -> None:
    hz, speed = 2.0, 300.0

    def signals(t):
        # A violent landing inside the settle, then a steady swing; the
        # linear joint's acceleration is in mm/s^2 and is not pooled.
        kick = 1.0e5 if t < 0.5 else 0.0
        return ([0.0, 0.0], [sine(speed, hz, t) + kick * t, sine(1.0e4, hz, t)],
                [0.0, 0.0], [0.0, 0.0])

    series = evaluation.drive_series(frames(signals), [channel("hip"), channel("slide", angular=False)])
    read = evaluation.drive_metrics(series)
    expected = speed * 2.0 * math.pi * hz / math.sqrt(2.0)
    assert read["joint_acceleration_rms_deg_s2"] == pytest.approx(expected, rel=0.02)
    assert read["drives"]["channels"][1]["joint_acceleration_rms"] > 10.0 * expected

    linear = evaluation.drive_series(frames(signals), [channel("slide", angular=False)])
    assert evaluation.drive_metrics(linear)["joint_acceleration_rms_deg_s2"] is None


def test_power_above_three_strides_is_jitter_and_below_it_is_the_gait() -> None:
    stride = 1.25

    def smooth(t):
        # A stride with its second harmonic: the shape of a gait, not jitter.
        command = sine(30.0, stride, t) + sine(10.0, 2.0 * stride, t + 0.1)
        return [0.0], [0.0], [command], [0.0]

    def jittery(t):
        return [0.0], [0.0], [sine(30.0, stride, t) + sine(30.0, 8.0 * stride, t)], [0.0]

    clean = evaluation.drive_metrics(evaluation.drive_series(frames(smooth), [channel("a")]),
                                     stride_hz=stride)
    noisy = evaluation.drive_metrics(evaluation.drive_series(frames(jittery), [channel("a")]),
                                     stride_hz=stride)
    assert clean["command_high_frequency_share"] < 0.01
    assert noisy["command_high_frequency_share"] == pytest.approx(0.5, abs=0.02)
    assert noisy["drives"]["high_frequency_hz"] == pytest.approx(3.0 * stride)

    series = evaluation.drive_series(frames(jittery), [channel("a")])
    # No stride, or a cutoff above the 25 Hz Nyquist limit: nothing measured.
    assert evaluation.drive_metrics(series)["command_high_frequency_share"] is None
    assert evaluation.drive_metrics(series, stride_hz=9.0)["command_high_frequency_share"] is None


def test_the_worst_drive_is_named_against_its_clamp() -> None:
    def signals(t):
        # "hock" sits at its +9 N·m clamp a fifth of the time and at 3 N·m
        # otherwise; "hip" never reaches its clamp; "free" has none.
        hock = 9000.0 if (t % 1.0) < 0.2 - 1e-9 else 3000.0
        return [0.0] * 3, [0.0] * 3, [0.0] * 3, [hock, -4000.0, 1.0e6]

    series = evaluation.drive_series(frames(signals), [
        channel("hock"), channel("hip"), channel("free", effort=None)])
    read = evaluation.drive_metrics(series)
    assert read["effort_clamp_share_max"] == pytest.approx(0.2, abs=0.005)
    rms = math.sqrt(0.2 * 9000.0 ** 2 + 0.8 * 3000.0 ** 2)
    assert read["effort_rms_clamp_ratio_max"] == pytest.approx(rms / 9000.0, rel=0.01)
    rows = {row["actuator"]: row for row in read["drives"]["channels"]}
    assert rows["hip"]["effort_clamp_share"] == 0.0
    assert rows["hip"]["effort_rms_clamp_ratio"] == pytest.approx(4000.0 / 9000.0)
    assert rows["free"]["effort_limit"] is None and rows["free"]["effort_clamp_share"] is None

    unlimited = evaluation.drive_series(frames(signals), [channel("free", effort=None)])
    assert evaluation.drive_metrics(unlimited)["effort_clamp_share_max"] is None


def test_cost_of_transport_is_mechanical_power_over_weight_times_speed() -> None:
    # Two drives each delivering 1 N·m at 1 rad/s, one braking: 2 W of
    # mechanical power, |effort x velocity| summed, on 20 N moving 0.5 m/s.
    one_rad_s = 180.0 / math.pi

    def signals(t):
        return [0.0, 0.0], [one_rad_s, -one_rad_s], [0.0, 0.0], [1000.0, 1000.0]

    series = evaluation.drive_series(frames(signals), [channel("a"), channel("b")])
    read = evaluation.drive_metrics(series, weight_n=20.0, travel=(4500.0, 9.0))
    assert read["drives"]["mean_power_nmm_s"] == pytest.approx(2000.0)
    assert read["cost_of_transport"] == pytest.approx(2.0 / (20.0 * 0.5))
    assert evaluation.drive_metrics(series, weight_n=20.0, travel=(0.0, 9.0))["cost_of_transport"] is None
    assert evaluation.drive_metrics(series)["cost_of_transport"] is None


def test_measure_reads_the_drive_family_from_the_trace_with_the_gaits_stride() -> None:
    period_frames = 24  # a 0.48 s stride
    samples = trot(period_frames=period_frames)
    stride = 1.0 / (period_frames * DT)

    def signals(t):
        return ([sine(20.0, stride, t)], [sine(20.0 * 2.0 * math.pi * stride, stride, t + 0.12)],
                [sine(20.0, stride, t) + sine(2.0, 10.0 * stride, t)], [1500.0])

    rig = {**walk_rig(), "weight_n": 30.0}
    drives = evaluation.drive_series(frames(signals), [channel("hip")])
    measured = evaluation.measure(samples, DONE, rig, drives=drives)
    metrics = measured["metrics"]
    for name, (family, _needs) in evaluation.METRICS.items():
        if family == "drive":
            assert isinstance(metrics[name], float), name
    for foot in measured["detail"]["feet"].values():
        assert foot["step_rate_hz"] == pytest.approx(stride, rel=0.05)
    assert measured["detail"]["drives"]["stride_hz"] == pytest.approx(stride, rel=0.05)
    # 2^2 / (20^2 + 2^2) of the power is the tenth harmonic.
    assert metrics["command_high_frequency_share"] == pytest.approx(4.0 / 404.0, rel=0.1)
    # The trot moves 80 mm/s; the hip's power is 1.5 N·m x |velocity|.
    assert metrics["cost_of_transport"] > 0.0

    without = evaluation.measure(samples, DONE, rig)
    assert not {name for name, (family, _n) in evaluation.METRICS.items() if family == "drive"} \
        & set(without["metrics"])
    assert "drives" not in without["detail"]


def test_a_spec_can_bound_the_drive_family() -> None:
    def signals(t):
        return [0.0], [0.0], [sine(30.0, 1.0, t)], [9000.0 if t < 2.0 else 0.0]

    read = evaluation.drive_metrics(evaluation.drive_series(frames(signals), [channel("a")]))
    rows = evaluation.check([
        {"id": "smooth", "metric": "command_rate_rms", "max": 1.0},
        {"id": "clamp", "metric": "effort_clamp_share_max", "max": 0.1},
        {"id": "cot", "metric": "cost_of_transport", "max": 1.0},
    ], read)
    assert [row["pass"] for row in rows] == [True, False, False]
    assert rows[2]["why"] == "cost_of_transport was not measured"
