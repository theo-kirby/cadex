# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``record_steps`` -- an episode that keeps its numbers and not its history.

``evaluate_episode`` returns one dict per control step in ``steps``: the
action, every observation, every reward term -- 6.1 kB a step on mg-legs
(ADR-136). ``record_steps=False`` drops that list and keeps everything else.

The ``endless`` horizon and the ``forces`` hook that once lived beside it
served only the live policy session, which went with the shell (ADR-528);
the last test here holds that they stay gone.

What this suite pins:

* a bounded episode stops at the task's horizon;
* ``record_steps=False`` empties ``steps`` and leaves ``step_count``,
  ``total_reward``, ``terminated_step`` and ``samples`` exactly as they were;
* and the defaults are the old loop, which is what keeps every rollout,
  trace and digest that exists today unmoved.
"""

from __future__ import annotations

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


def test_a_bounded_episode_still_stops_at_the_tasks_horizon() -> None:
    """The horizon is the task's, and nothing extends it (ADR-528)."""

    make_model, task = _bundle()
    episode = dyn.evaluate_episode(make_model(), task)

    assert episode["step_count"] == HORIZON
    assert episode["truncated"] is True
    assert episode["terminated_step"] is None


def test_record_steps_false_keeps_every_number_and_drops_the_history() -> None:
    make_model, task = _bundle()
    recorded = dyn.evaluate_episode(make_model(), task)
    silent = dyn.evaluate_episode(make_model(), task, record_steps=False)

    assert silent["steps"] == []
    assert silent["step_count"] == recorded["step_count"] == HORIZON
    # Bit for bit: the reward is still evaluated every step and still summed,
    # so a caller that keeps no history still knows how it went.
    assert silent["total_reward"] == recorded["total_reward"]
    assert silent["terminated_step"] == recorded["terminated_step"]
    assert silent["truncated"] == recorded["truncated"]
    assert silent["termination"] == recorded["termination"]


def test_record_steps_false_leaves_the_sample_hook_alone() -> None:
    """The ``sample`` seam a rollout reads through is untouched by the flag."""

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


def test_the_live_session_keywords_are_gone() -> None:
    """``forces`` and ``endless`` had one caller, the live worker (ADR-528)."""

    import inspect

    parameters = inspect.signature(dyn.evaluate_episode).parameters
    assert "forces" not in parameters
    assert "endless" not in parameters
    make_model, task = _bundle()
    with pytest.raises(TypeError):
        dyn.evaluate_episode(make_model(), task, endless=True)
