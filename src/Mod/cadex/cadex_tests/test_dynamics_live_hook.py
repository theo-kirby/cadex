# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The ``forces`` seam live mode is built on (ADR-109).

One new keyword on ``evaluate_episode``, and the whole of what live mode
needed from the episode loop. It exists because ``apply_disturbance`` writes
``xfrc_applied`` **from zero** every control step -- deliberately, so a
window that closed stops pushing -- which means a shove written from outside
the loop survives exactly until the next step and then vanishes. A hook
placed immediately after that write is the one position where an outside
force can be additive to the task's own.

What this suite pins:

* it runs once per control step, after the disturbance and before the
  action, with the same ``time_s`` the disturbance was applied at;
* what it writes reaches the integrator -- a hook that pushed and changed
  nothing would be a seam in name only;
* on a task that declares **no** disturbance the array is still cleared
  every step, because ``apply_disturbance`` returns before its own clear in
  that case and a live push would otherwise accumulate step on step into a
  force nobody applied;
* and the same on a task that **does** declare one, played **unseeded** --
  nothing is drawn, so that function again writes nothing and clears nothing.
  That is live mode's calm session (ADR-110), and the guard shipped reading
  only the task half of the condition;
* it composes with a declared disturbance rather than replacing it;
* and ``forces=None`` is bit-for-bit the episode that ran before it existed.

That last one is the one that matters most. The hook is **not** a digest
input and consumes nothing from the RNG stream, so a bundle written before
it must replay identically -- and this project has four implementations of
one RNG contract, with M9's hazard 19 recording what happened when two of
them disagreed unnoticed.
"""

from __future__ import annotations

import math

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

#: A shove big enough to move a 300 mm arm in a fifth of a second and small
#: enough not to be a collision test.
PUSH_N = 4.0


def _bundle(**task_overrides):
    """A model **factory** and the bundle built from its exported bytes.

    A factory rather than a model, for ADR-103 section 9's reason:
    ``apply_randomisation`` multiplies its draws into the ``MjModel`` in
    place with no baseline kept, so two episodes played on one model are the
    second one played on a mechanism the first one deformed. Every
    comparison in this file is between two episodes, so every one of them
    would otherwise be comparing two different machines.
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


def _arm_body(model) -> int:
    return int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "arm"))


def _pusher(body, newtons=PUSH_N, axis=0, record=None):
    """A hook that shoves the arm along one world axis, every step."""

    def forces(step, data, time_s):
        if record is not None:
            record.append((int(step), float(time_s)))
        data.xfrc_applied[body, axis] += float(newtons)

    return forces


def _last_arm_z(episode) -> float:
    return float(episode["steps"][-1]["observation"]["arm_z"])


def _trajectory(episode) -> list[float]:
    return [float(step["observation"]["arm_z"]) for step in episode["steps"]]


# ---------------------------------------------------------------------------
# It runs, in the right place, at the right times.
# ---------------------------------------------------------------------------


def test_the_hook_runs_once_per_control_step_on_the_step_clock() -> None:
    make_model, task = _bundle()
    model = make_model()
    seen: list[tuple[int, float]] = []
    episode = dyn.evaluate_episode(
        model, task, forces=_pusher(_arm_body(model), record=seen), seed=1
    )

    interval = float(task["episode"]["control_interval_s"])
    assert [index for index, _ in seen] == list(range(len(seen)))
    assert len(seen) == len(episode["steps"])
    # The same clock ``apply_disturbance`` reads, so a live push and a drawn
    # one are placed on the timeline by the same arithmetic rather than by
    # two spellings of it.
    for index, time_s in seen:
        assert time_s == pytest.approx(index * interval)


def test_what_the_hook_writes_reaches_the_integrator() -> None:
    """A seam that pushed and changed nothing would be a seam in name only."""

    make_model, task = _bundle()
    body = _arm_body(make_model())
    still = dyn.evaluate_episode(make_model(), task, seed=1)
    shoved = dyn.evaluate_episode(
        make_model(), task, forces=_pusher(body), seed=1
    )
    assert _last_arm_z(still) != pytest.approx(_last_arm_z(shoved), abs=1e-9)

    # ...and it is the *push* that did it, not the hook merely being present.
    nothing = dyn.evaluate_episode(
        make_model(), task, forces=_pusher(body, newtons=0.0), seed=1
    )
    assert _trajectory(nothing) == _trajectory(still)


def test_a_bigger_push_moves_it_further() -> None:
    """The measurement that says the number reached the physics, not a flag.

    A hook wired to a boolean instead of to a magnitude passes every test
    above this one. This is the one that fails (M9 hazard 18: a curve that
    does not move measured nothing).
    """

    make_model, task = _bundle()
    body = _arm_body(make_model())
    still = _last_arm_z(dyn.evaluate_episode(make_model(), task, seed=1))
    displacement = [
        abs(
            _last_arm_z(
                dyn.evaluate_episode(
                    make_model(), task,
                    forces=_pusher(body, newtons=newtons), seed=1,
                )
            )
            - still
        )
        for newtons in (0.0, PUSH_N, 2.0 * PUSH_N)
    ]
    assert displacement[0] == pytest.approx(0.0, abs=1e-12)
    assert 0.0 < displacement[1] < displacement[2]


# ---------------------------------------------------------------------------
# The clearing rule, which is the whole reason the hook is where it is.
# ---------------------------------------------------------------------------


def test_a_push_does_not_accumulate_on_a_task_with_no_disturbance() -> None:
    """``apply_disturbance`` returns before its own clear when there is none.

    So the loop performs the clear instead when a hook is present. Without
    it, a hook adding 4 N a step would be applying 4, 8, 12... newtons -- a
    force nobody asked for, growing linearly, and invisible from outside
    because the trajectory would still look like a push.
    """

    make_model, task = _bundle()
    assert not task["disturbance"], "this fixture must declare no push"
    model = make_model()
    body = _arm_body(model)
    observed: list[float] = []

    def forces(_step, data, _time_s):
        # Read BEFORE writing: what the array holds at the top of a step is
        # whatever the last step left in it.
        observed.append(float(data.xfrc_applied[body, 0]))
        data.xfrc_applied[body, 0] += PUSH_N

    dyn.evaluate_episode(model, task, forces=forces, seed=1)
    assert observed, "the hook never ran"
    assert observed == [0.0] * len(observed)


def test_a_push_does_not_accumulate_on_an_unseeded_episode() -> None:
    """The same rule, on the other half of the same condition (ADR-110).

    ``apply_disturbance`` returns early on ``not entries or not draws``, and
    the loop's guard originally read only the *entries* half. So on a task
    that **does** declare a disturbance, played **unseeded** -- nothing is
    drawn, so nothing is written and nothing is cleared -- a hook adding 4 N
    a step was applying 4, 8, 12... newtons.

    That combination is not a corner: it is live mode's calm session, which
    is exactly ``seed=None`` on a task whose bundle declares shoves. Found by
    asking for one.
    """

    make_model, task = _bundle(
        disturbance=[
            {
                "label": "shove",
                "component": "arm",
                "direction": "horizontal",
                "newtons_low": 1.0,
                "newtons_high": 3.0,
                "sustained": False,
                "at_seconds_low": 0.05,
                "at_seconds_high": 0.15,
                "duration_s": 0.05,
            }
        ]
    )
    assert task["disturbance"], "this fixture must declare a push"
    model = make_model()
    body = _arm_body(model)
    observed: list[float] = []

    def forces(_step, data, _time_s):
        observed.append(float(data.xfrc_applied[body, 0]))
        data.xfrc_applied[body, 0] += PUSH_N

    dyn.evaluate_episode(model, task, forces=forces, seed=None)
    assert observed, "the hook never ran"
    assert observed == [0.0] * len(observed), (
        "an unseeded episode draws no disturbance, so apply_disturbance "
        "writes nothing and clears nothing; the loop owes the clear."
    )


def test_a_push_is_added_on_top_of_the_tasks_own_disturbance() -> None:
    """Composition, not replacement: a user shoves a machine already shoved."""

    make_model, task = _bundle(
        disturbance=[
            {
                "label": "gust",
                "component": "arm",
                "direction": "horizontal",
                "newtons_low": 10.0,
                "newtons_high": 10.0,
                "sustained": True,
                "at_seconds_low": 0.0,
                "at_seconds_high": 0.0,
                "duration_s": 0.0,
            }
        ]
    )
    model = make_model()
    body = _arm_body(model)
    drawn: list[float] = []
    total: list[float] = []

    def forces(_step, data, _time_s):
        drawn.append(
            math.hypot(float(data.xfrc_applied[body, 0]),
                       float(data.xfrc_applied[body, 1]))
        )
        data.xfrc_applied[body, 2] += PUSH_N
        total.append(float(data.xfrc_applied[body, 2]))

    dyn.evaluate_episode(model, task, forces=forces, seed=1)
    # The declared 10 N horizontal shove is still in the array when the hook
    # sees it, and the hook's vertical newtons land on top of it rather than
    # instead of it.
    assert drawn[0] == pytest.approx(10.0, abs=1e-9)
    assert total == [pytest.approx(PUSH_N)] * len(total)


# ---------------------------------------------------------------------------
# ...and it changes nothing for anybody who does not pass it.
# ---------------------------------------------------------------------------


def test_forces_is_additive_and_defaults_to_the_episode_that_existed() -> None:
    """Not a digest input, and it consumes nothing from the RNG stream."""

    make_model, task = _bundle(
        randomisation=[
            {"target": "mass", "component": "arm", "low": 0.9, "high": 1.1,
             "label": "arm_mass"}
        ],
        disturbance=[
            {
                "label": "shove",
                "component": "arm",
                "direction": "horizontal",
                "newtons_low": 1.0,
                "newtons_high": 3.0,
                "sustained": False,
                "at_seconds_low": 0.05,
                "at_seconds_high": 0.15,
                "duration_s": 0.05,
            }
        ],
    )
    plain = dyn.evaluate_episode(make_model(), task, seed=7)
    with_noop = dyn.evaluate_episode(
        make_model(), task, forces=lambda *_args: None, seed=7
    )
    assert _trajectory(plain) == _trajectory(with_noop)
    assert plain["disturbance"] == with_noop["disturbance"]
    assert plain["total_reward"] == with_noop["total_reward"]

    # The algorithm string is a digest input and the hook is not named in
    # it. A sentence that mentioned an outside force would make every bundle
    # written before live mode a different bundle -- including the one the
    # policy live mode exists to play.
    assert "forces" not in dyn.EPISODE_VARIATION_ALGORITHM
