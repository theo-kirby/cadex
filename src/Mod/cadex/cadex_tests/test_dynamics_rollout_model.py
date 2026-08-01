# SPDX-License-Identifier: LGPL-2.1-or-later

"""``rollout_policy`` in the pure module (docs/MUJOCO.md M8, phase 1).

No FreeCAD, no worker, no protocol: a compiled model, a task bundle, a
policy container, and the frames the shell plays. What is tested here is the
half of M8 that is arithmetic and schema; the half that is graph validation
is in ``test_dynamics_rollout_api``, and the half that is a live engine is in
``test_dynamics_policy_live``.

The claims worth testing rather than reading:

* **The frame schema is ``simulate``'s**, exactly -- an untimed ``input``
  frame in front, ``solver_output`` frames after it, millimetres and xyzw,
  every component in every frame. ``cadex_animate`` has baked that schema
  since ADR-050 and a rollout that wrote a fourth dialect of it would be a
  bake the viewport declines with nothing to point at.
* **``frames_per_second`` divides ``control_hz``**, which is the control-step
  form of ``simulate``'s solver-step rule. Phase 0 measured what 50 Hz played
  at 60 fps does.
* **The last state is always recorded.** An episode that terminates between
  two frame boundaries would otherwise end its trace before the thing that
  ended it.
"""

from __future__ import annotations

import pytest

import CadexDynamics as dyn

mujoco = pytest.importorskip("mujoco")

import dynamics_policy_fixtures as pf  # noqa: E402

COMPONENTS = ["post", "link"]


def _prepared(**task):
    """A swing-up bundle and a policy container built against it."""

    prepared = pf.swing_up_bundle(
        task={**pf.SWING_UP_TASK, **task} if task else None
    )
    prepared["container"] = pf.policy_container(prepared, normalise=True)
    prepared["reloaded"] = dyn.load_model(prepared["model_xml"])
    return prepared


def _rollout(prepared, *, frames_per_second=50, seed=None, components=None):
    return dyn.rollout_policy(
        prepared["reloaded"],
        prepared["bundle"],
        prepared["container"],
        components=list(COMPONENTS if components is None else components),
        frames_per_second=frames_per_second,
        seed=seed,
    )


#: The horizon-running variant: random weights spin the real swing-up out
#: after about sixty steps, and a schema assertion about a trace that ended
#: early is an assertion about the wrong thing.
def _full(**task):
    return _prepared(termination=[], **task)


# ---------------------------------------------------------------------------
# The schema the shell plays.
# ---------------------------------------------------------------------------


def test_the_frames_are_the_schema_cadex_animate_already_bakes() -> None:
    run = _rollout(_full())
    frames = run["frames"]

    assert frames[0]["frame_index"] == 0
    assert frames[0]["frame_kind"] == "input"
    assert frames[0]["nominal_time_s"] is None
    assert all(frame["frame_kind"] == "solver_output" for frame in frames[1:])
    assert [frame["frame_index"] for frame in frames] == list(range(len(frames)))

    # The solved frame at t=0 sits behind the input frame and is not it --
    # simulate's first contract detail, found by running M1's prototype
    # against cadex_animate rather than by reading it.
    assert frames[1]["nominal_time_s"] == 0.0
    assert (frames[1]["component_placements"]
            == frames[0]["component_placements"])

    for frame in frames:
        placements = frame["component_placements"]
        assert sorted(placements) == sorted(COMPONENTS)
        for pose in placements.values():
            assert len(pose["position_mm"]) == 3
            assert len(pose["rotation_xyzw"]) == 4
            assert all(isinstance(value, float) for value in pose["position_mm"])


def test_positions_are_millimetres_and_the_mechanism_actually_moved() -> None:
    """Metres would be a thousandth of a mechanism, and it would still bake."""

    run = _rollout(_full())
    frames = run["frames"]
    link_z = [frame["component_placements"]["link"]["position_mm"][2]
              for frame in frames]

    # The link is hinged 150 mm up a 300 mm post, so its own origin sits
    # there and stays there; the arm swings around it.
    assert link_z[0] == pytest.approx(150.0, abs=1.0e-6)
    rotations = [frame["component_placements"]["link"]["rotation_xyzw"]
                 for frame in frames]
    assert max(abs(a - b) for a, b in zip(rotations[0], rotations[-1])) > 1.0e-3, (
        "the link never moved, so this trace would bake a still mechanism"
    )
    # The grounded post does not move at all, whatever the policy does.
    assert all(
        frame["component_placements"]["post"]["position_mm"] == [0.0, 0.0, 0.0]
        for frame in frames
    )


@pytest.mark.parametrize(
    "frames_per_second,expected_steps_per_frame,expected_frames",
    [(50, 1, 102), (25, 2, 52), (10, 5, 22), (5, 10, 12), (1, 50, 4)],
)
def test_one_frame_per_n_control_steps_and_the_arithmetic_says_which(
    frames_per_second: int, expected_steps_per_frame: int, expected_frames: int
) -> None:
    """100 control steps at 50 Hz, sampled five ways.

    ``max_steps // steps_per_frame + 1`` solver frames plus the input frame,
    and no rounding anywhere: that is what "divides exactly" buys.
    """

    run = _rollout(_full(), frames_per_second=frames_per_second)
    assert run["frames_per_second"] == frames_per_second
    assert run["steps_per_frame"] == expected_steps_per_frame
    assert len(run["frames"]) == expected_frames
    assert run["frame_interval_s"] == pytest.approx(1.0 / frames_per_second)
    assert run["frames"][-1]["nominal_time_s"] == pytest.approx(2.0)


@pytest.mark.parametrize("rate", [60, 3, 30, 240, 7])
def test_a_frame_rate_that_does_not_divide_the_control_rate_is_refused(rate) -> None:
    """Phase 0's measurement, as a refusal that names the rates that work."""

    with pytest.raises(dyn.DynamicsError) as excinfo:
        _rollout(_full(), frames_per_second=rate)
    error = excinfo.value
    assert error.reason == "frame_rate_indivisible"
    assert "50 Hz" in str(error)
    assert "1, 2, 5, 10, 25, 50" in error.correction
    assert error.observed["frames_per_second"] == rate


def test_the_default_frame_rate_is_one_frame_per_control_step() -> None:
    """The only rate that always divides ``control_hz``: ``control_hz``."""

    prepared = _full()
    control_hz = int(prepared["bundle"]["episode"]["control_hz"])
    run = _rollout(prepared, frames_per_second=control_hz)
    assert run["steps_per_frame"] == 1


# ---------------------------------------------------------------------------
# Hazard 5: a component missing from a frame is not an error the shell
# reports -- it interpolates the gap, and a part that stops moving looks like
# a physics result.
# ---------------------------------------------------------------------------


def test_a_component_the_exported_model_does_not_carry_is_refused_by_name() -> None:
    with pytest.raises(dyn.DynamicsError) as excinfo:
        _rollout(_full(), components=["post", "link", "gantry"])
    error = excinfo.value
    assert error.reason == "rollout_component_missing"
    assert "'gantry'" in str(error)
    assert error.observed["component"] == "gantry"


def test_every_component_appears_in_every_frame() -> None:
    """The refusal above's positive half, asserted per frame rather than once."""

    run = _rollout(_full())
    for frame in run["frames"]:
        assert set(frame["component_placements"]) == set(COMPONENTS)


# ---------------------------------------------------------------------------
# The episode the frames came from.
# ---------------------------------------------------------------------------


def test_the_summary_reports_the_episode_and_its_reward_terms() -> None:
    run = _rollout(_full())
    episode = run["episode"]

    assert episode["label"] == "swing_up"
    assert episode["step_count"] == 100
    assert episode["control_hz"] == 50
    assert episode["truncated"] is True
    assert episode["terminated_step"] is None
    assert episode["termination"] == ""
    assert episode["episode_seconds"] == pytest.approx(2.0)

    labels = [term["label"] for term in episode["reward_totals"]]
    assert labels == ["height", "spin"]
    assert sum(term["total"] for term in episode["reward_totals"]) == pytest.approx(
        episode["total_reward"]
    )


def test_a_terminated_episode_records_its_last_state_whatever_the_frame_rate() -> None:
    """The trace ends where the episode did, not at the previous boundary.

    The real swing-up terminates when the hinge exceeds 3000 deg/s, which a
    policy of random weights manages in about sixty steps -- and sixty is not
    a multiple of ten. Without the final sample the trace would stop up to
    nine control steps before the thing that ended it.
    """

    prepared = _prepared()
    run = _rollout(prepared, frames_per_second=5)  # one frame per 10 steps
    episode = run["episode"]

    assert episode["truncated"] is False
    assert episode["termination"] == "spun_out"
    assert episode["terminated_step"] is not None
    assert episode["step_count"] % run["steps_per_frame"] != 0, (
        "this fixture no longer terminates between two frame boundaries, so "
        "it no longer tests what it was written for"
    )
    assert run["frames"][-1]["nominal_time_s"] == pytest.approx(
        episode["episode_seconds"]
    )
    # ...and the final frame is a frame, not a duplicate of the one before.
    assert (run["frames"][-1]["component_placements"]
            != run["frames"][-2]["component_placements"])


def test_the_solver_facts_are_read_off_the_model_that_ran() -> None:
    prepared = _full()
    run = _rollout(prepared)
    assert run["solver_step_s"] == pytest.approx(
        float(prepared["reloaded"].opt.timestep)
    )
    assert run["solver_tolerance"] == pytest.approx(
        float(prepared["reloaded"].opt.tolerance)
    )


# ---------------------------------------------------------------------------
# Determinism, which is what the trace's digest rests on (ADR-068).
# ---------------------------------------------------------------------------


def test_two_rollouts_of_one_policy_produce_identical_frames() -> None:
    prepared = _full()
    assert _rollout(prepared)["frames"] == _rollout(prepared)["frames"]


_RANDOMISED = [
    {"target": "mass", "label": "link_mass", "component": "link",
     "low": 0.5, "high": 1.5},
]


def test_a_seed_reproduces_its_draws_and_a_different_seed_changes_them() -> None:
    """The randomisation half, which is the only thing ``seed`` touches."""

    first = _rollout(_full(randomisation=_RANDOMISED), seed=4)
    again = _rollout(_full(randomisation=_RANDOMISED), seed=4)
    other = _rollout(_full(randomisation=_RANDOMISED), seed=5)

    assert first["frames"] == again["frames"]
    assert first["episode"]["seed"] == 4
    assert [entry["label"] for entry in first["episode"]["randomisation"]] == [
        "link_mass"
    ]
    assert first["episode"]["randomisation"] == again["episode"]["randomisation"]
    assert first["episode"]["randomisation"] != other["episode"]["randomisation"]
    assert first["frames"] != other["frames"]


def test_without_a_seed_nothing_is_randomised() -> None:
    run = _rollout(_full(randomisation=_RANDOMISED))
    assert run["episode"]["seed"] is None
    assert run["episode"]["randomisation"] == []


# ---------------------------------------------------------------------------
# The budget. Frames are what the artifact carries and poses are what the
# shell bakes; what the solver does is bounded when the bundle is built.
# ---------------------------------------------------------------------------


def test_a_rollout_that_would_produce_too_many_frames_is_refused_before_it_runs() -> None:
    """3600 s at 50 Hz is 180 000 frames, which is eighteen times the cap."""

    prepared = _full(episode_seconds=3600.0)
    with pytest.raises(dyn.DynamicsError) as excinfo:
        _rollout(prepared, frames_per_second=50)
    error = excinfo.value
    assert error.reason == "rollout_budget_exceeded"
    assert error.observed["frames"] > dyn.MAXIMUM_TRACE_FRAMES
    assert error.observed["maximum_frames"] == dyn.MAXIMUM_TRACE_FRAMES
    assert "frames_per_second" in error.correction


def test_the_same_episode_played_slowly_enough_fits_the_budget() -> None:
    """The refusal above is about the frame rate, so lowering it is the fix."""

    prepared = _full(episode_seconds=3600.0)
    run = _rollout(prepared, frames_per_second=1)
    assert len(run["frames"]) == 3602
    assert len(run["frames"]) * len(COMPONENTS) <= dyn.MAXIMUM_TRACE_POSES


# ---------------------------------------------------------------------------
# What M8 did NOT add, which is the point of the slice.
# ---------------------------------------------------------------------------


def test_the_episode_loop_gained_a_sampler_and_not_a_second_loop() -> None:
    """One episode loop stays one episode loop.

    M7 already carries three evaluators of the reward whitelist. A rollout
    with its own stepping loop would be a fourth place for the same drift,
    so ``evaluate_episode`` gained a ``sample`` callable and nothing else --
    and a rollout's own reward has to equal the one an undriven call to it
    computes for the same actions.
    """

    prepared = _full()
    container = prepared["container"]

    def actions(_step, observation):
        return dyn.policy_forward(
            container["header"], container["weights"], observation
        )

    direct = dyn.evaluate_episode(
        prepared["reloaded"], prepared["bundle"], actions=actions
    )
    run = _rollout(prepared)

    assert run["episode"]["total_reward"] == direct["total_reward"]
    assert run["episode"]["step_count"] == direct["step_count"]
    # ...and a call with no sampler collects nothing, so every existing
    # caller -- the worker's task loop, the reference runner, the trainer --
    # is untouched.
    assert direct["samples"] == []


# ---------------------------------------------------------------------------
# The commands the policy issued, which are the one thing the poses do not
# already show.
# ---------------------------------------------------------------------------


def test_every_solved_frame_carries_the_command_that_produced_it() -> None:
    """One command vector per actuator per frame, and none on the reset.

    The poses say what the mechanism did; only this says what the policy
    decided. The reset frame and the untimed ``input`` frame in front of it
    carry no command because no action has been taken there -- and a row of
    zeros would not do, because zero is a command a policy can issue.
    """

    prepared = _full()
    run = _rollout(prepared)
    channels = run["actuator_channels"]
    assert [channel["actuator"] for channel in channels] == [
        action["actuator"] for action in prepared["bundle"]["actions"]
    ]

    frames = run["frames"]
    assert "actuator_commands" not in frames[0]
    assert "actuator_commands" not in frames[1]
    commanded = [frame for frame in frames if "actuator_commands" in frame]
    assert len(commanded) == len(frames) - 2
    assert all(
        len(frame["actuator_commands"]) == len(channels) for frame in commanded
    )


def test_the_recorded_command_is_the_clamped_one() -> None:
    """What reached ``data.ctrl``, not what the network said.

    A policy saturates: it commands past its own advertised range and the
    episode loop clamps before scaling. A frame carrying the unclamped
    number would describe a motor the model does not have, so the value
    recorded is the applied one -- which is exactly the ``action`` the
    episode's own step record carries.
    """

    prepared = _full()
    run = _rollout(prepared, frames_per_second=50)
    channels = run["actuator_channels"]

    for frame in run["frames"]:
        for value, channel in zip(frame.get("actuator_commands") or (), channels):
            assert channel["low"] <= value <= channel["high"]

    # The same numbers the loop wrote, taken from the other side: at one
    # frame per control step every step's applied action is a frame.
    container = prepared["container"]

    def actions(_step, observation):
        return dyn.policy_forward(
            container["header"], container["weights"], observation
        )

    control_hz = int(prepared["bundle"]["episode"]["control_hz"])
    dense = _rollout(prepared, frames_per_second=control_hz)
    direct = dyn.evaluate_episode(
        prepared["reloaded"], prepared["bundle"], actions=actions
    )
    recorded = [
        frame["actuator_commands"]
        for frame in dense["frames"]
        if "actuator_commands" in frame
    ]
    assert recorded == [step["action"] for step in direct["steps"]]


def test_a_channel_states_the_range_its_command_is_read_against() -> None:
    """A torque is a number; a torque against its limit is a reading.

    The range is what makes the value worth drawing, and it comes from the
    bundle -- a motor's effort limit, a servo's joint limits -- rather than
    from anything the trace invents.
    """

    prepared = _full()
    channels = _rollout(prepared)["actuator_channels"]
    for channel, action in zip(channels, prepared["bundle"]["actions"]):
        assert channel["low"] == action["low"]
        assert channel["high"] == action["high"]
        assert channel["unit"] == action["unit"]
        assert channel["low"] < channel["high"]
