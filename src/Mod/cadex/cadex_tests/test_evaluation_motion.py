# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The motion family: what a body did about a centre over an episode (ADR-587).

A spec that bounds only where a body ended passes a body that rocked on an
arc and stopped on the circle. These pin the reading that tells the two
apart: net signed turns, laps, and distance from a point, on traces whose
answers are stated -- a circle, a rock on the same arc, an episode cut
short, and a centre carried by a frame that tilts and turns.
"""

from __future__ import annotations

import math

import pytest

import CadexEvaluation as evaluation
from evaluation_fixtures import DONE, DT, IDENTITY

RADIUS = 40.0
CUT = {"duration_s": 1.0, "termination": "ball_off_plate", "truncated": False, "seed": 1}


def rig(*, frame=None, point=(0.0, 0.0, 0.0), axis=(0.0, 0.0, 1.0)):
    return {"base": None, "body": {"body": "ball", "local_mm": [0.0, 0.0, 0.0]},
            "centre": {"frame": frame, "point_mm": list(point), "axis": list(axis)}}


def samples(angles, *, radius=RADIUS, plate=lambda _t: (IDENTITY, [0.0, 0.0, 0.0])):
    """A ball at ``radius`` and the given bearing (radians) in the plate's frame."""

    rows = []
    for index, angle in enumerate(angles):
        time_s = index * DT
        quat, origin = plate(time_s)
        rotation = evaluation.matrix(quat)
        local = (radius * math.cos(angle), radius * math.sin(angle), 0.0)
        world = [o + sum(rotation[i][k] * local[k] for k in range(3)) for i, o in enumerate(origin)]
        rows.append((time_s, {"ball": {"position_mm": world, "rotation_xyzw": IDENTITY},
                              "plate": {"position_mm": list(origin), "rotation_xyzw": quat}}))
    return rows


def circling(laps=3.0, frames=500, sign=1.0):
    return [sign * 2.0 * math.pi * laps * i / (frames - 1) for i in range(frames)]


def rocking(frames=500, swing=1.2, period=40):
    """Out along an arc and back, about a third of a turn each way, many times."""

    return [swing * math.sin(2.0 * math.pi * i / period) for i in range(frames)]


def approx(value):
    return pytest.approx(value, rel=1e-6, abs=1e-6)


LAPS = [{"id": "circulates", "metric": "laps", "min": 2.0},
        {"id": "on_circle", "metric": "final_distance_mm", "min": 30.0, "max": 50.0}]


def judged(trace, episode=DONE, **arguments):
    measured = evaluation.measure(trace, episode, rig(**arguments))
    return measured, evaluation.check(LAPS, measured["metrics"])


def test_a_circling_trace_passes_a_laps_predicate() -> None:
    measured, rows = judged(samples(circling(3.0)))
    assert measured["metrics"]["turns"] == approx(3.0)
    assert measured["metrics"]["laps"] == 3.0
    assert all(row["pass"] for row in rows)


def test_a_rocking_trace_on_the_same_arc_fails_it_and_ends_on_the_circle() -> None:
    """circle-6's failure: on the circle at the end, and going nowhere."""

    measured, rows = judged(samples(rocking()))
    assert abs(measured["metrics"]["turns"]) < 0.05
    assert measured["metrics"]["laps"] == 0.0
    by_id = {row["id"]: row for row in rows}
    assert by_id["on_circle"]["pass"] and not by_id["circulates"]["pass"]


def test_turns_are_signed_and_laps_count_the_net_direction() -> None:
    clockwise = evaluation.measure(samples(circling(2.5, sign=-1.0)), DONE, rig())["metrics"]
    assert clockwise["turns"] == approx(-2.5)
    assert clockwise["laps"] == 2.0
    # Seen from below, the same motion is anticlockwise.
    flipped = evaluation.measure(samples(circling(2.5, sign=-1.0)), DONE,
                                 rig(axis=(0.0, 0.0, -1.0)))["metrics"]
    assert flipped["turns"] == approx(2.5)


def test_a_trace_that_ends_early_fails_rather_than_crashes() -> None:
    for trace in (samples(circling(3.0)[:50]), samples(circling(3.0)[:1]), []):
        measured, rows = judged(trace, episode=CUT)
        assert all(measured["metrics"][name] is None for name in
                   ("turns", "laps", "final_distance_mm", "mean_distance_mm", "max_distance_mm"))
        assert not any(row["pass"] for row in rows)
        assert all(row["why"].endswith("was not measured") for row in rows)
        # What was played is still there to read, marked as partial.
        assert measured["detail"]["motion"]["partial"] is True
    played = judged(samples(circling(3.0)[:50]), episode=CUT)[0]["detail"]["motion"]
    assert played["frames"] == 50 and 0.25 < played["turns"] < 0.35


def test_distance_needs_no_goal_and_reads_final_mean_and_max() -> None:
    radii = [30.0 - 0.05 * i for i in range(500)]
    trace = []
    for index, radius in enumerate(radii):
        trace.append((index * DT, {"ball": {"position_mm": [radius, 0.0, 12.5],
                                            "rotation_xyzw": IDENTITY}}))
    metrics = evaluation.measure(trace, DONE, rig(point=(0.0, 0.0, 12.5)))["metrics"]
    assert metrics["final_distance_mm"] == approx(radii[-1])
    assert metrics["max_distance_mm"] == approx(30.0)
    assert metrics["mean_distance_mm"] == approx(sum(radii) / len(radii))
    assert "final_error_mm_max" not in metrics


def test_the_centre_moves_with_its_frame_through_a_tilt_and_a_turn() -> None:
    """A ball that circles on a plate which tilts and spins is judged on the plate."""

    def plate(time_s):
        # Tilt 10 degrees about X, then spin about world Z at a quarter
        # turn a second, on a pivot 110 mm up.
        spin, tilt = math.radians(90.0) * time_s, math.radians(10.0)
        q_tilt = [math.sin(tilt / 2.0), 0.0, 0.0, math.cos(tilt / 2.0)]
        q_spin = [0.0, 0.0, math.sin(spin / 2.0), math.cos(spin / 2.0)]
        x1, y1, z1, w1 = q_spin
        x2, y2, z2, w2 = q_tilt
        quat = [w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2]
        return quat, [5.0, -3.0, 110.0]

    on_plate = evaluation.measure(samples(circling(2.0), plate=plate), DONE,
                                  rig(frame="plate"))["metrics"]
    assert on_plate["turns"] == approx(2.0)
    assert on_plate["mean_distance_mm"] == approx(RADIUS)
    # Held still on the spinning plate: no turns about the plate's centre,
    # while the world sees it go round with the plate.
    held = samples([0.3] * 500, plate=plate)
    assert abs(evaluation.measure(held, DONE, rig(frame="plate"))["metrics"]["turns"]) < 1e-9
    world = evaluation.measure(held, DONE, rig(point=(5.0, -3.0, 110.0)))["metrics"]
    assert world["turns"] > 2.0


def test_every_motion_metric_needs_a_body_and_is_in_the_vocabulary() -> None:
    names = {"turns", "laps", "final_distance_mm", "mean_distance_mm", "max_distance_mm"}
    assert {name for name, (family, _needs) in evaluation.METRICS.items()
            if family == "motion"} == names
    assert all(evaluation.METRICS[name][1] == ("body",) for name in names)
    # A rig with no body reads no motion.
    assert not names & set(evaluation.measure(samples(circling()), DONE, {"base": None})["metrics"])

