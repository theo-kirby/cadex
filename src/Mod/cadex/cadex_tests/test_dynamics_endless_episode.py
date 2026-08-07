# SPDX-License-Identifier: LGPL-2.1-or-later

"""``endless`` and ``record_steps`` -- the episode live mode plays (ADR-136).

Live mode used to stop every six seconds and start again, because it played
the task's episode and the task's episode is the length a *trainer* wanted.
Nothing physical happens at that number: an observation is sensor channels
and carries no clock, so the policy cannot tell step 301 from step 5. The
horizon is a truncation for something that needs episodes to end, and a
person watching a machine stand up is not that.

So two keywords, both defaulting to what every other caller already had:

* ``endless`` drops the horizon -- the loop runs until a termination rule
  fires or a hook unwinds it;
* ``record_steps=False`` stops the ``steps`` list accumulating, which is the
  only thing that made an unbounded episode unaffordable. It is one dict per
  control step holding the action, every observation and every reward term
  -- 6.1 kB a step on mg-legs, measured at +553 MB for half an hour of
  simulation against +1.6 MB with the flag -- and live mode reads none of it.

What this suite pins:

* an endless episode runs past ``max_steps`` and keeps stepping;
* it still ends on a termination rule, at the same step a bounded episode
  would have ended on -- dropping the horizon must not change the physics;
* ``truncated`` is false for it, because it had no budget to use;
* ``record_steps=False`` empties ``steps`` and leaves ``step_count``,
  ``total_reward``, ``terminated_step`` and ``samples`` exactly as they were;
* and the defaults are the old loop, which is what keeps every rollout,
  trace and digest that exists today unmoved.
"""

from __future__ import annotations

import threading

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx

mujoco = pytest.importorskip("mujoco")


MOTOR = {
    "joint": "hinge",
    "motion_type": "angular",
    "kind": "motor",
    "control_nmm": "0",
    "torque_limit_nmm": 50.0,
}

OBSERVATIONS = [
    {"kind": "component_position", "component": "arm", "name": "arm"},
    {"kind": "component_linear_velocity", "component": "arm", "name": "vel"},
]

TASK = {
    "actions": [
        {"joint": "hinge", "motion_type": "angular", "actuator_kind": "motor"}
    ],
    "reward": [{"label": "height", "expression": "arm_z", "weight": 1.0e-3}],
    "termination": [],
    "episode_seconds": 0.4,
    "control_hz": 50,
    "randomisation": [],
    "reset_variation": [],
    "disturbance": [],
    "label": "swing",
}

#: Control steps the task above declares. Everything here is measured
#: against it, so it is derived rather than written twice.
HORIZON = int(round(TASK["episode_seconds"] * TASK["control_hz"]))


class _Stop(BaseException):
    """What live mode's own unwind is, in one line.

    ``BaseException`` for the reason the worker's is: the loop it interrupts
    is arithmetic with no ``except Exception`` in it, but the evaluators
    around it are defensive.
    """


def _bundle(**task_overrides):
    """A model **factory** and the bundle built from its exported bytes.

    A factory rather than a model, for ADR-103 section 9's reason:
    ``apply_randomisation`` multiplies its draws into the ``MjModel`` in
    place with no baseline kept, so two episodes played on one model are the
    second one played on a mechanism the first one deformed.
    """

    components, joints, _placements = fx.pendulum()
    built = dyn.build_model(components, joints, actuators=[dict(MOTOR)])
    observations = dyn.observation_records(
        list(OBSERVATIONS),
        built["tree"],
        built["joint_records"],
        built["actuators"],
    )
    exported = dyn.export_mjcf(built, observations=observations)
    xml = exported["xml"].decode("utf-8")
    reloaded = mujoco.MjModel.from_xml_string(xml)
    task = dict(TASK)
    task.update(task_overrides)
    bundle = dyn.task_records(built, reloaded, task, observations=observations)
    return (lambda: mujoco.MjModel.from_xml_string(xml)), bundle


def _stopper(at: int, seen: list[int] | None = None):
    """A ``forces`` hook that unwinds the episode after ``at`` steps."""

    def forces(step, data, time_s):
        if seen is not None:
            seen.append(int(step))
        if step >= at:
            raise _Stop()

    return forces


# ---------------------------------------------------------------------------
# It runs past the horizon.
# ---------------------------------------------------------------------------


def test_a_bounded_episode_still_stops_at_the_tasks_horizon() -> None:
    """The control: this is what live mode used to do every six seconds."""

    make_model, task = _bundle()
    episode = dyn.evaluate_episode(make_model(), task)

    assert episode["step_count"] == HORIZON
    assert episode["truncated"] is True
    assert episode["terminated_step"] is None


def test_an_endless_episode_runs_past_the_horizon() -> None:
    make_model, task = _bundle()
    beyond = HORIZON * 4
    seen: list[int] = []

    with pytest.raises(_Stop):
        dyn.evaluate_episode(
            make_model(), task, forces=_stopper(beyond, seen), endless=True
        )

    # Not "it did not stop at 20" -- it reached 80, one step at a time, with
    # no gap. A loop that ran twice as long by some other route would pass a
    # bare inequality and fail this.
    assert seen == list(range(beyond + 1))


def test_the_horizon_is_the_only_thing_endless_drops() -> None:
    """Up to the old horizon, the two episodes are the same machine."""

    make_model, task = _bundle()
    bounded = dyn.evaluate_episode(make_model(), task)

    endless_steps: list[float] = []

    def sample(step, data, final, action):
        # Read through the bundle's own observation slices, so this is the
        # same number by the same route as ``steps[...]["observation"]``
        # rather than a second opinion in different units.
        endless_steps.append(
            float(dyn.observation_values(task, data.sensordata)["arm_z"])
        )
        return None

    with pytest.raises(_Stop):
        dyn.evaluate_episode(
            make_model(), task, sample=sample, forces=_stopper(HORIZON * 2),
            endless=True,
        )

    # The sample hook fires at the reset pose and after every step, so the
    # bounded episode's N steps are entries 1..N here.
    for index, step in enumerate(bounded["steps"]):
        assert endless_steps[index + 1] == pytest.approx(
            step["observation"]["arm_z"], rel=0, abs=1e-12
        )


# ---------------------------------------------------------------------------
# It still ends when the mechanism does.
# ---------------------------------------------------------------------------


def test_an_endless_episode_still_terminates_and_is_not_truncated() -> None:
    """A fall ends it -- at the step it would have ended a long episode on.

    The threshold is *measured* rather than written down: a long bounded
    episode is played first and the step it crosses is read off it. That
    makes this a comparison between two runs of the same physics instead of
    a number that drifts when the fixture does.
    """

    make_model, long_task = _bundle(episode_seconds=1.0)
    probe = dyn.evaluate_episode(make_model(), long_task)
    heights = [step["observation"]["arm_z"] for step in probe["steps"]]

    # A height the arm is above at the short horizon and below well after
    # it, so "endless" is what makes the rule reachable at all. The arm
    # swings, so the crossing is read as the FIRST one -- a later threshold
    # would be met on the way back up and pin the wrong step.
    floor = min(heights)
    threshold = floor + (max(heights) - floor) * 0.5
    expected = next(
        index for index, height in enumerate(heights) if height < threshold
    )

    # A horizon deliberately shorter than that crossing: the whole point is
    # a rule the bounded episode never reaches.
    short_seconds = 0.06
    short_horizon = int(round(short_seconds * TASK["control_hz"]))
    assert expected > short_horizon, (
        "the fixture no longer crosses its own threshold after the short "
        f"horizon (crossed at step {expected}, horizon {short_horizon}) -- "
        "this test proves nothing until that is true again"
    )

    make_model, task = _bundle(
        episode_seconds=short_seconds,
        termination=[{"label": "fell", "expression": "arm_z",
                      "below": threshold}],
    )

    bounded = dyn.evaluate_episode(make_model(), task)
    assert bounded["terminated_step"] is None
    assert bounded["truncated"] is True

    endless = dyn.evaluate_episode(make_model(), task, endless=True)
    assert endless["terminated_step"] == expected
    assert endless["termination"] == "fell"
    # It had no budget to use up, so it cannot have been cut short of one.
    assert endless["truncated"] is False
    assert endless["step_count"] == expected + 1


# ---------------------------------------------------------------------------
# Not recording changes the bookkeeping and nothing else.
# ---------------------------------------------------------------------------


def test_record_steps_false_keeps_every_number_and_drops_the_history() -> None:
    make_model, task = _bundle()
    recorded = dyn.evaluate_episode(make_model(), task)
    silent = dyn.evaluate_episode(make_model(), task, record_steps=False)

    assert silent["steps"] == []
    assert silent["step_count"] == recorded["step_count"] == HORIZON
    # Bit for bit: the reward is still evaluated every step and still summed,
    # so a session that keeps no history still knows how it is doing.
    assert silent["total_reward"] == recorded["total_reward"]
    assert silent["terminated_step"] == recorded["terminated_step"]
    assert silent["truncated"] == recorded["truncated"]
    assert silent["termination"] == recorded["termination"]


def test_record_steps_false_leaves_the_sample_hook_alone() -> None:
    """The seam live mode actually reads through is untouched by the flag."""

    make_model, task = _bundle()
    with_history = []
    without_history = []

    def _collect(into):
        def sample(step, data, final, action):
            into.append((int(step), bool(final),
                         None if action is None else list(action)))
            return None
        return sample

    dyn.evaluate_episode(make_model(), task, sample=_collect(with_history))
    dyn.evaluate_episode(
        make_model(), task, sample=_collect(without_history),
        record_steps=False,
    )

    assert without_history == with_history
    assert without_history[0] == (0, False, None)
    assert without_history[-1][0] == HORIZON
    assert without_history[-1][1] is True


def test_an_endless_episode_never_calls_its_sample_hook_final() -> None:
    """``final`` means "this episode is over", and this one is not.

    Live mode's ``sample`` streams a frame every step; a ``final`` that
    arrived every horizon's worth of steps would be a lie the shell has no
    way to check.
    """

    finals: list[bool] = []

    def sample(step, data, final, action):
        finals.append(bool(final))
        return None

    make_model, task = _bundle()
    with pytest.raises(_Stop):
        dyn.evaluate_episode(
            make_model(), task, sample=sample,
            forces=_stopper(HORIZON * 2), endless=True,
        )

    assert finals and not any(finals)


# ---------------------------------------------------------------------------
# The defaults are the loop that was there before.
# ---------------------------------------------------------------------------


def test_the_live_worker_asks_for_exactly_that_episode() -> None:
    """The one line that would make all of the above decorative.

    Driven directly rather than through a session, for the reason
    ``test_the_open_frame_carries_variation_and_an_uncoerced_seed`` gives:
    the behaviour is two process boundaries away, and this is the boundary
    where it would be lost. ``_dyn`` is a stub, so no physics runs and the
    episode "ends" the moment it is asked for.
    """

    import pathlib
    import sys

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    try:
        import cadex_live_worker as worker
    finally:
        sys.path.pop(0)

    calls: list[dict] = []
    session = object.__new__(worker._Session)

    class _Dyn:
        def load_model(self, _xml):
            return object()

        def evaluate_episode(self, _model, _task, **kwargs):
            calls.append(kwargs)
            # One episode and stop, so this exercises the call rather than
            # the loop around it -- which has its own reasons to spin.
            session._closing = True
            return {"terminated_step": 3, "termination": "fell"}

    session._dyn = _Dyn()
    session._lock = threading.Lock()
    session._wake = threading.Condition(session._lock)
    session._boundary = threading.Event()
    session._closing = False
    session._credit = 0
    session._episode = 0
    session._seed = 11
    session._variation = True
    session._reset_count = 0
    session._step = 0
    session._time_s = 0.0
    session._terminated = False
    session._termination = ""
    session._push = None
    session._model_xml = b"<mujoco/>"
    session._task = {}
    session._actions = None
    session._sample = None
    session._forces = None

    session._run()

    assert len(calls) == 1
    assert calls[0]["endless"] is True
    assert calls[0]["record_steps"] is False
    # Still the seeded/calm distinction ADR-110 fixed -- dropping the horizon
    # must not quietly re-coerce this.
    assert calls[0]["seed"] == 11


def test_the_defaults_are_the_old_loop() -> None:
    """Every rollout, trace and digest in the tree rides on this.

    ``step_count`` stopped being ``len(steps)`` and became a counter, which
    is exactly the kind of change that is correct until it is off by one.
    """

    make_model, task = _bundle()
    episode = dyn.evaluate_episode(make_model(), task)

    assert episode["step_count"] == len(episode["steps"])
    assert [step["step"] for step in episode["steps"]] == list(range(HORIZON))
    assert all(step["reward_terms"] for step in episode["steps"])
    assert episode["total_reward"] == pytest.approx(
        sum(step["reward"] for step in episode["steps"])
    )
