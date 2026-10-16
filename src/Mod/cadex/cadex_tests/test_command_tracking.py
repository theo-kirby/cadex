# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""A commanded yaw rate, scripted goal openings, and command tracking (ADR-721).

A task can command a floating base to turn (``kind="yaw_rate"``, deg/s about
world +Z, anticlockwise positive), a goal's opening segments can be scripted
so every evaluation seed asks the same reversal, and a success spec can bound
how closely a base followed commands that change: speed and yaw-rate RMS
error outside a settling window after each change, and the heading error of
a commanded 180-degree turn at the moment the command has done it.
"""

from __future__ import annotations

import copy
import math
import random

import pytest

import CadexDynamics as dyn
import CadexEvaluation as evaluation
import cadex_assembly_api

# -- the tracking family, pure ------------------------------------------------

RIG = {"base": "body", "reference_xyzw": [0.0, 0.0, 0.0, 1.0],
       "base_com_local_mm": [0.0, 0.0, 0.0]}
HZ = 50


def _commands(segments):
    """``[(seconds, value)]`` held in turn, one value per 50 Hz frame."""

    return [value for seconds, value in segments for _ in range(int(round(seconds * HZ)))]


def _drive(speed_cmd, yaw_cmd, *, speed=lambda i, v: v, yaw=lambda i, w: w):
    """A base that moves at ``speed(i, commanded)`` mm/s along its heading and
    turns at ``yaw(i, commanded)`` deg/s: integrated exactly, frame by frame."""

    samples, heading, x, y = [], 0.0, 0.0, 0.0
    for i in range(len(speed_cmd)):
        samples.append((i / HZ, {"body": {
            "position_mm": [x, y, 300.0],
            "rotation_xyzw": [0.0, 0.0, math.sin(math.radians(heading) / 2),
                              math.cos(math.radians(heading) / 2)]}}))
        v, w = speed(i, speed_cmd[i]), yaw(i, yaw_cmd[i])
        # Move along the mid-step heading, so the windowed speed is exact.
        mid = math.radians(heading + 0.5 * w / HZ)
        x, y = x + v / HZ * math.cos(mid), y + v / HZ * math.sin(mid)
        heading += w / HZ
    return samples


SPEED = _commands([(2.0, 1000.0), (3.0, 1500.0), (3.0, 800.0)])
REVERSE = _commands([(2.0, 0.0), (3.0, 60.0), (3.0, -20.0)])


def test_a_base_that_follows_every_command_tracks_with_no_error() -> None:
    read = evaluation.tracking_metrics(_drive(SPEED, REVERSE), RIG,
                                       {"speed": SPEED, "yaw_rate": REVERSE})
    assert read["speed_error_rms_mm_s"] == pytest.approx(0.0, abs=0.5)
    assert read["yaw_rate_error_rms_deg_s"] == pytest.approx(0.0, abs=1e-6)
    (reversal,) = read["tracking"]["reversals"]
    assert reversal["start_s"] == pytest.approx(2.0)
    assert reversal["due_s"] == pytest.approx(5.0)
    assert read["reversal_heading_error_deg_max"] == pytest.approx(0.0, abs=1e-6)
    assert read["tracking"]["command_changes_s"] == pytest.approx([2.0, 5.0])


def test_a_constant_shortfall_reads_its_own_size() -> None:
    samples = _drive(SPEED, REVERSE, speed=lambda i, v: v - 100.0, yaw=lambda i, w: w - 5.0)
    read = evaluation.tracking_metrics(samples, RIG, {"speed": SPEED, "yaw_rate": REVERSE})
    assert read["speed_error_rms_mm_s"] == pytest.approx(100.0, rel=1e-3)
    assert read["yaw_rate_error_rms_deg_s"] == pytest.approx(5.0, rel=1e-6)
    # Three seconds at 55 deg/s instead of 60: 15 degrees short of 180.
    assert read["reversal_heading_error_deg_max"] == pytest.approx(15.0, abs=0.2)


def test_the_moments_after_a_command_changes_are_not_charged() -> None:
    """A base that ignores each new command for 0.4 s, then follows it: the
    settling window drops those frames, so it reads as exact. Ignoring it for
    a whole second does not hide."""

    changes = [int(2.0 * HZ), int(5.0 * HZ)]

    def late(by_s):
        def follow(i, w):
            for start in changes:
                if start <= i < start + int(by_s * HZ):
                    return REVERSE[start - 1]
            return w
        return follow

    quick = evaluation.tracking_metrics(_drive(SPEED, REVERSE, yaw=late(0.24)), RIG,
                                        {"yaw_rate": REVERSE})
    assert quick["yaw_rate_error_rms_deg_s"] == pytest.approx(0.0, abs=1e-6)
    assert quick["speed_error_rms_mm_s"] is None
    slow = evaluation.tracking_metrics(_drive(SPEED, REVERSE, yaw=late(1.0)), RIG,
                                       {"yaw_rate": REVERSE})
    assert slow["yaw_rate_error_rms_deg_s"] > 10.0


def test_a_turn_cut_short_or_never_commanded_is_no_reversal() -> None:
    short = _commands([(2.0, 0.0), (2.0, 60.0), (2.0, 0.0)])
    read = evaluation.tracking_metrics(_drive(_commands([(6.0, 1000.0)]), short), RIG,
                                       {"yaw_rate": short})
    assert read["tracking"]["reversals"] == []
    assert read["reversal_heading_error_deg_max"] is None
    assert read["yaw_rate_error_rms_deg_s"] == pytest.approx(0.0, abs=1e-6)
    # The last command holds to the episode's end: 3 s at -60 is a reversal.
    held = _commands([(1.0, 0.0), (3.02, -60.0)])
    read = evaluation.tracking_metrics(_drive(_commands([(4.02, 0.0)]), held), RIG,
                                       {"yaw_rate": held})
    assert read["reversal_heading_error_deg_max"] == pytest.approx(0.0, abs=1e-6)
    # ...and a predicate on an unmeasured reversal fails rather than passes.
    (row,) = evaluation.check([{"id": "reverses", "metric": "reversal_heading_error_deg_max",
                                "max": 20.0}], {"reversal_heading_error_deg_max": None})
    assert not row["pass"]


def test_measure_reads_the_tracking_family_only_when_commands_are_handed_in() -> None:
    samples = _drive(SPEED, REVERSE)
    episode = {"truncated": True, "termination": "", "duration_s": 8.0}
    rig = {**RIG, "com_height_mm": None}
    read = evaluation.measure(samples, episode, rig,
                              commands={"speed": SPEED, "yaw_rate": REVERSE})
    assert read["metrics"]["yaw_rate_error_rms_deg_s"] == pytest.approx(0.0, abs=1e-6)
    assert "reversals" in read["detail"]["tracking"]
    assert "yaw_rate_error_rms_deg_s" not in evaluation.measure(samples, episode, rig)["metrics"]


def test_the_tracking_family_is_in_the_vocabulary_with_its_needs() -> None:
    assert evaluation.METRICS["speed_error_rms_mm_s"] == ("tracking", ("base", "command"))
    for name in ("yaw_rate_error_rms_deg_s", "reversal_heading_error_deg_max"):
        assert evaluation.METRICS[name] == ("tracking", ("base", "turn"))


# -- the API ----------------------------------------------------------------

def _api():
    from test_success_spec_api import _api as made

    return made()


def test_a_yaw_rate_goal_and_a_scripted_opening_on_the_surface() -> None:
    assert "yaw_rate" in cadex_assembly_api._GOAL_KINDS
    turn = _api().goal("turn", kind="yaw_rate", between=[-60, 60],
                       resample_seconds=1.0, sequence=[0, 0, 60, 60, 60])
    assert turn.properties["kind"] == "yaw_rate"
    assert list(turn.properties["sequence"]) == [0.0, 0.0, 60.0, 60.0, 60.0]


@pytest.mark.parametrize("arguments", [
    {"kind": "yaw_rate", "between": [-60, 60], "sequence": [90]},
    {"kind": "yaw_rate", "between": [-60, 60], "sequence": []},
    {"kind": "yaw_rate", "between": [-60, 60], "sequence": "60"},
    {"kind": "phase", "period_seconds": 1.0, "sequence": [0.5]},
])
def test_a_sequence_outside_its_range_or_on_the_wrong_kind_is_refused(arguments) -> None:
    with pytest.raises(Exception) as raised:
        _api().goal("turn", **arguments)
    assert "sequence" in str(raised.value)


# -- the bundle and the draw (stock MuJoCo) -----------------------------------

mujoco = pytest.importorskip("mujoco")

TURN = {"name": "turn", "kind": "yaw_rate", "low": -60.0, "high": 60.0,
        "resample_seconds": 0.4, "sequence": [0.0, 60.0]}


def _turning():
    from test_dynamics_goal_model import COMMAND, WALK_TASK
    from test_success_spec_model import MOTORS, OBSERVATIONS, walker

    task = {**WALK_TASK, "goal": [{**COMMAND, "resample_seconds": 0.4}, TURN]}
    return task, {"mechanism": walker, "motors": MOTORS, "observations": OBSERVATIONS}


def test_a_yaw_rate_goal_lands_in_the_bundle_with_its_script_and_algorithm() -> None:
    from test_dynamics_goal_model import made

    task, walker = _turning()
    bundle = made(task, **walker)["bundle"]
    turn = bundle["goal"][1]
    assert (turn["kind"], turn["unit"], turn["channels"]) == ("yaw_rate", "deg/s", ["turn"])
    assert turn["sequence"] == [0.0, 60.0]
    assert bundle["goal_algorithm"] == dyn.GOAL_ALGORITHM + dyn.GOAL_SEQUENCE_ALGORITHM
    plain = made({**task, "goal": [task["goal"][0], {**TURN, "sequence": None}]},
                 **walker)["bundle"]
    assert "sequence" not in plain["goal"][1]
    assert plain["goal_algorithm"] == dyn.GOAL_ALGORITHM


def test_engine_runner_and_trainer_draw_a_scripted_goal_alike() -> None:
    """The scripted segments hold their script, every other segment is the
    unscripted draw, and the stream is left where the unscripted one is."""

    import dynamics_task_episode as runner
    from test_dynamics_goal_model import made, model
    from test_dynamics_policy_trainer import _trainer_module

    task, walker = _turning()
    prepared = made(task, **walker)
    bundle = prepared["bundle"]
    plain = copy.deepcopy(bundle)
    del plain["goal"][1]["sequence"]
    compiled = model(prepared)
    for seed in (0, 7, 1101):
        streams = [random.Random(seed) for _ in range(4)]
        engine = dyn.draw_episode_goals(mujoco, compiled, bundle, streams[0])
        assert runner.draw_goals(mujoco, compiled, bundle, streams[1]) == engine
        assert _trainer_module().draw_goals(mujoco, compiled, bundle, streams[2]) == engine
        unscripted = dyn.draw_episode_goals(mujoco, compiled, plain, streams[3])
        segments = engine[1]["segments"]
        assert segments[:2] == [[0.0], [60.0]]
        assert segments[2:] == unscripted[1]["segments"][2:]
        assert engine[0] == unscripted[0]
        assert len({stream.random() for stream in streams}) == 1


def test_the_engine_refuses_a_second_yaw_rate_and_a_script_out_of_range() -> None:
    from test_dynamics_goal_model import made

    task, walker = _turning()
    with pytest.raises(dyn.DynamicsError) as twice:
        made({**task, "goal": task["goal"] + [{**TURN, "name": "spin", "sequence": None}]},
             **walker)
    assert twice.value.reason == "duplicate_goal_kind"
    assert "yaw rate" in twice.value.correction
    with pytest.raises(dyn.DynamicsError) as wide:
        made({**task, "goal": [task["goal"][0], {**TURN, "sequence": [90.0]}]}, **walker)
    assert wide.value.reason == "malformed_goal"


def test_a_turning_predicate_on_a_task_that_commands_no_turn_is_refused() -> None:
    from test_success_spec_model import refusal, spec

    error = refusal(spec([{"id": "turns", "metric": "yaw_rate_error_rms_deg_s", "max": 20.0}]))
    assert error.reason == "success_metric_needs_turn"
    assert "yaw_rate" in error.correction
