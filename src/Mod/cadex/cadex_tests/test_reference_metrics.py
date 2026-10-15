# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The reference family: a gait against the task's gait reference (ADR-705).

Each metric is pinned on a synthetic trot whose answer is stated -- the
fixture trot's diagonal pairs land together every 0.48 s and are down half
the stride -- against a hand-written ``cadex-gait-clip-v1`` reference, with
no physics: a trot reference reads no footfall error, a pace reference reads
two feet half a cycle out, a joint that follows the clip's shape through its
own stride reads no joint error whatever its stride frequency, and a joint
held 5 degrees off reads 5.
"""

from __future__ import annotations

import math

import pytest

import CadexEvaluation as evaluation
from evaluation_fixtures import DONE, DT, trot, walk_rig
from evaluation_fixtures import drive_channel as channel
from evaluation_fixtures import drive_frames as frames

#: The fixture trot moves ``fl`` with ``rr`` and ``fr`` with ``rl``; the
#: reference's left hind is ``rl``, so its partner is the right fore.
LEGS = {"LF": "fl", "RF": "fr", "LH": "rl", "RH": "rr"}
TROT = {"LH": 0.0, "RF": 0.0, "RH": 0.5, "LF": 0.5}
PACE = {"LH": 0.0, "LF": 0.0, "RH": 0.5, "RF": 0.5}
PERIOD_FRAMES = 24  # the fixture's stride: 0.48 s
SAMPLES = 24
AMPLITUDE_DEG = 20.0


def clip(offsets=TROT, *, duty=0.5, period_s=PERIOD_FRAMES * DT, gait="trot"):
    """A reference: one joint, ``hip_joint``, swinging a sine over the stride."""

    return {
        "schema": "cadex-gait-clip-v1", "gait": gait,
        "parameters": {"phase_offsets": dict(offsets), "duty_factor": duty,
                       "stride_frequency_hz": 1.0 / period_s, "period_s": period_s},
        "legs": {label: {"foot_body": name, "joints": []} for label, name in LEGS.items()},
        "joints": ["hip_joint"],
        "joint_angles_rad": [[math.radians(AMPLITUDE_DEG * math.sin(2.0 * math.pi * k / SAMPLES))]
                             for k in range(SAMPLES)],
    }


def walked(period_frames=PERIOD_FRAMES):
    samples = trot(period_frames=period_frames)
    return samples, evaluation.gait_metrics(samples, walk_rig())["feet"]


def hip(period_s: float, *, bias_deg: float = 0.0):
    """A drive whose joint follows the clip's sine through its own stride.

    The fixture's left hind (``rl``) lands at every whole stride, so the
    reference's phase at ``t`` is ``t / period_s``.
    """

    def signals(t):
        angle = AMPLITUDE_DEG * math.sin(2.0 * math.pi * t / period_s) + bias_deg
        return [angle], [0.0], [0.0], [0.0]

    return evaluation.drive_series(frames(signals), [channel("hip")])


def test_a_landing_is_the_first_stance_frame_after_a_step() -> None:
    _, feet = walked()
    landings = feet["rl"]["touchdowns_s"]
    assert len(landings) == feet["rl"]["steps"]
    period = PERIOD_FRAMES * DT
    assert all(abs(t / period - round(t / period)) < 1e-9 for t in landings)


def test_a_trot_against_its_own_reference_reads_no_footfall_error() -> None:
    _, feet = walked()
    read = evaluation.reference_metrics(feet, clip())
    assert read["footfall_phase_error_max"] == pytest.approx(0.0, abs=1e-9)
    assert read["duty_factor_error_max"] == pytest.approx(0.0, abs=0.03)
    assert read["stride_frequency_ratio"] == pytest.approx(1.0, rel=1e-6)
    detail = read["reference"]
    assert detail["anchor"] == "rl" and detail["strides"] >= 15
    assert {row["expected_phase"] for row in detail["feet"].values()} == {0.0, 0.5}
    assert all(row["missed_strides"] == 0 for row in detail["feet"].values())
    # No drive record: the footfall is measured, the joints are not.
    assert read["reference_joint_rms_deg"] is None


def test_a_pace_reference_reads_the_lateral_pair_half_a_cycle_out() -> None:
    _, feet = walked()
    read = evaluation.reference_metrics(feet, clip(PACE, gait="pace"))
    assert read["footfall_phase_error_max"] == pytest.approx(0.5)
    rows = read["reference"]["feet"]
    assert rows["LF"]["phase_error"] == pytest.approx(0.5)
    assert rows["RF"]["phase_error"] == pytest.approx(0.5)
    assert rows["RH"]["phase_error"] == pytest.approx(0.0, abs=1e-9)


def test_a_foot_a_tenth_of_a_cycle_off_its_offset_reads_a_tenth() -> None:
    _, feet = walked()
    late = clip({**TROT, "LF": 0.6})
    assert evaluation.reference_metrics(feet, late)["footfall_phase_error_max"] == pytest.approx(0.1)
    # The duty factor is the reference's less the gait's, worst foot.
    assert evaluation.reference_metrics(feet, clip(duty=0.3))[
        "duty_factor_error_max"] == pytest.approx(0.2, abs=0.03)


def test_the_joints_are_compared_pose_for_pose_through_each_stride() -> None:
    samples, feet = walked()
    on = evaluation.reference_metrics(feet, clip(), drives=hip(PERIOD_FRAMES * DT))
    assert on["reference_joint_rms_deg"] == pytest.approx(0.0, abs=1e-6)
    assert on["reference"]["joints"] == [{"joint": "hip_joint", "rms_deg": on["reference_joint_rms_deg"]}]
    off = evaluation.reference_metrics(feet, clip(), drives=hip(PERIOD_FRAMES * DT, bias_deg=5.0))
    assert off["reference_joint_rms_deg"] == pytest.approx(5.0, rel=1e-6)
    # A drive whose joint the clip does not pose is not compared.
    other = evaluation.drive_series(frames(lambda t: ([90.0], [0.0], [0.0], [0.0])), [channel("tail")])
    assert evaluation.reference_metrics(feet, clip(), drives=other)["reference_joint_rms_deg"] is None


def test_a_slower_stride_is_aligned_by_its_own_landings_and_its_timing_is_a_ratio() -> None:
    # 30-frame strides against a 24-frame reference: the shape still matches,
    # and the frequency reads 0.8 of the reference's.
    slow = 30
    _, feet = walked(slow)
    read = evaluation.reference_metrics(feet, clip(), drives=hip(slow * DT))
    assert read["stride_frequency_ratio"] == pytest.approx(PERIOD_FRAMES / slow, rel=1e-6)
    # Off the clip's samples now: only the linear interpolation's chord error
    # on a 20-degree sine sampled 24 times, under a tenth of a degree.
    assert read["reference_joint_rms_deg"] == pytest.approx(0.0, abs=0.1)
    assert read["footfall_phase_error_max"] == pytest.approx(0.0, abs=1e-9)


def test_measure_reads_the_family_only_with_a_reference_and_feet() -> None:
    samples, _ = walked()
    drives = hip(PERIOD_FRAMES * DT)
    family = {name for name, (kind, _n) in evaluation.METRICS.items() if kind == "reference"}
    assert family == {"footfall_phase_error_max", "duty_factor_error_max",
                      "stride_frequency_ratio", "reference_joint_rms_deg"}
    measured = evaluation.measure(samples, DONE, walk_rig(), drives=drives, reference=clip())
    for name in family:
        assert isinstance(measured["metrics"][name], float), name
    assert measured["detail"]["reference"]["gait"] == "trot"
    without = evaluation.measure(samples, DONE, walk_rig(), drives=drives)
    assert not family & set(without["metrics"]) and "reference" not in without["detail"]
    rows = evaluation.check([{"id": "trots", "metric": "footfall_phase_error_max", "max": 0.1},
                             {"id": "tracks", "metric": "reference_joint_rms_deg", "max": 10.0}],
                            measured["metrics"])
    assert [row["pass"] for row in rows] == [True, True]


def test_nothing_is_measured_without_a_stride_or_with_a_foot_missing() -> None:
    samples, feet = walked()
    short = evaluation.reference_metrics(
        {name: {**foot, "touchdowns_s": foot["touchdowns_s"][:1]} for name, foot in feet.items()},
        clip())
    assert short["reference"]["strides"] == 0
    assert all(short[name] is None for name in (
        "footfall_phase_error_max", "duty_factor_error_max",
        "stride_frequency_ratio", "reference_joint_rms_deg"))
    missing = evaluation.reference_metrics({k: v for k, v in feet.items() if k != "rr"}, clip())
    assert missing["reference"]["missing_feet"] == ["rr"]
    assert missing["footfall_phase_error_max"] is None


def test_a_foot_that_skips_a_stride_misses_it() -> None:
    _, feet = walked()
    # Drop every other landing of the right hind: half its strides are missed.
    skipping = {**feet, "rr": {**feet["rr"], "touchdowns_s": feet["rr"]["touchdowns_s"][::2]}}
    read = evaluation.reference_metrics(skipping, clip())
    row = read["reference"]["feet"]["RH"]
    strides = read["reference"]["strides"]
    assert strides // 2 - 1 <= row["missed_strides"] <= strides // 2 + 1
    assert read["reference"]["feet"]["LF"]["missed_strides"] == 0
