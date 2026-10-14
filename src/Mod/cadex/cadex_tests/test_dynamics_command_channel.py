# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A task can observe what it commanded, and so can say "smooth" (ADR-696).

A ``command`` observation reads the command in force on one of the task's
actuators -- the clamped action, after any filter or slew limit -- and its
change over the last control step, per second. As a policy input it is the
previous action; in a reward it is the action rate. No MJCF sensor carries
it, so the bundle states it in a ``commands`` section and every evaluator
computes it: the engine's episode loop, the trainer, and the stock-MuJoCo
reference runner. This file holds the three to one rule.

The last test runs the real trainer and is gated on its dependencies, as
``test_dynamics_policy_trainer`` is.
"""

from __future__ import annotations

import inspect
import math
import os
from pathlib import Path
import subprocess

import pytest

import CadexDynamics as dyn
import dynamics_policy_fixtures as pf
from test_dynamics_goal_model import (
    ARM_OBSERVATIONS,
    ARM_SERVOS,
    ARM_TASK,
    _stock,
    arm,
    made,
    model,
)
from test_dynamics_policy_trainer import TRAINER, _trainer_module, _venv_python

mujoco = pytest.importorskip("mujoco")

#: The arm's two servos, swept, so the commands move every step.
SWEPT = [
    {**servo, "control_deg": f"{20.0 + 10.0 * index}*sin(2*pi*{1.5 + index}*time)"}
    for index, servo in enumerate(ARM_SERVOS)
]
COMMANDED = [
    *ARM_OBSERVATIONS,
    {"kind": "command", "joint": "shoulder", "motion_type": "angular",
     "actuator_kind": "position", "name": "shoulder_cmd"},
    {"kind": "command", "joint": "elbow", "motion_type": "angular",
     "actuator_kind": "position", "name": "elbow_cmd", "role": "privileged"},
]
#: An action-rate penalty, the standard smoothness regulariser.
SMOOTH_TASK = {
    **{key: value for key, value in ARM_TASK.items() if key != "goal"},
    "reward": [
        {"label": "up", "expression": "hand_z", "weight": 1.0e-3},
        {"label": "action_rate",
         "expression": "-((shoulder_cmd_rate / 100)**2 + (elbow_cmd_rate / 100)**2)",
         "weight": 0.1},
    ],
}


def commanded(**overrides):
    return made(SMOOTH_TASK, motors=SWEPT, observations=COMMANDED, **overrides)


# -- the bundle -------------------------------------------------------------

def test_a_task_that_observes_no_command_is_the_bundle_it_always_was() -> None:
    """No key: every task written before ADR-696 keeps its digest."""

    bundle = pf.swing_up_bundle()["bundle"]
    assert "commands" not in bundle
    assert dyn._task_channels(bundle) == ["angle", "rate", "tip_x", "tip_y", "tip_z"]
    assert dyn.command_channels(bundle) == []


def test_a_command_is_a_row_of_its_own_after_the_sensors_and_carries_no_sensor() -> None:
    prepared = commanded()
    bundle = prepared["bundle"]

    assert bundle["commands"] == [
        {"name": "shoulder_cmd", "kind": "command", "target": "shoulder",
         "actuator": bundle["actions"][0]["actuator"], "action": 0,
         "channels": ["shoulder_cmd", "shoulder_cmd_rate"],
         "unit": "deg", "rate_unit": "deg/s"},
        {"name": "elbow_cmd", "kind": "command", "target": "elbow",
         "actuator": bundle["actions"][1]["actuator"], "action": 1,
         "channels": ["elbow_cmd", "elbow_cmd_rate"],
         "unit": "deg", "rate_unit": "deg/s", "role": "privileged"},
    ]
    # The file carries the two sensors it always did, and nothing else.
    assert [row["name"] for row in bundle["observations"]] == ["elbow_angle", "hand"]
    assert model(prepared).nsensor == 2
    assert dyn._task_channels(bundle) == [
        "elbow_angle", "hand_x", "hand_y", "hand_z",
        "shoulder_cmd", "shoulder_cmd_rate", "elbow_cmd", "elbow_cmd_rate",
    ]
    # A privileged command feeds the reward and the critic, not the policy;
    # and a command needs no sensor, because the controller knows it.
    assert dyn.policy_channels(bundle)[-2:] == ["shoulder_cmd", "shoulder_cmd_rate"]
    assert "elbow_cmd" not in dyn.policy_channels(bundle)
    assert dyn.ungrounded_policy_channels(bundle) == ["elbow_angle", "hand_x",
                                                      "hand_y", "hand_z"]


def test_a_command_off_an_actuator_the_task_does_not_drive_is_refused() -> None:
    only_shoulder = {**SMOOTH_TASK, "actions": SMOOTH_TASK["actions"][:1],
                     "reward": SMOOTH_TASK["reward"][:1]}
    with pytest.raises(dyn.DynamicsError) as raised:
        commanded(**only_shoulder)
    assert raised.value.reason == "command_not_an_action"


def test_one_actuator_is_commanded_once_and_its_names_clash_like_any_channel() -> None:
    twice = [*COMMANDED, {**COMMANDED[2], "name": "again"}]
    with pytest.raises(dyn.DynamicsError) as raised:
        made(SMOOTH_TASK, motors=SWEPT, observations=twice)
    assert raised.value.reason == "duplicate_command_observation"

    clash = [*COMMANDED, {"kind": "position", "joint": "shoulder",
                          "motion_type": "angular", "name": "shoulder_cmd_rate"}]
    with pytest.raises(dyn.DynamicsError) as raised:
        made(SMOOTH_TASK, motors=SWEPT, observations=clash)
    assert raised.value.reason == "duplicate_observation_channel"


def test_commands_do_not_count_against_the_sensor_cap() -> None:
    """The cap bounds the sensors in the file; one command per action
    bounds the rest. 64 sensor channels and two commands is accepted, 65
    sensor channels is not."""

    built = dyn.build_model(*arm()[:2],
                            actuators=[dict(servo) for servo in SWEPT])
    sensors = [{"kind": "position", "joint": "elbow", "motion_type": "angular",
                "name": f"p{index}"} for index in range(dyn.MAXIMUM_OBSERVATION_CHANNELS)]
    records = dyn.observation_records(sensors + COMMANDED[2:], built["tree"],
                                      built["joint_records"], built["actuators"])
    assert len(dyn.sensor_observations(records)) == dyn.MAXIMUM_OBSERVATION_CHANNELS
    with pytest.raises(dyn.DynamicsError) as raised:
        dyn.observation_records(
            sensors + [{**sensors[0], "name": "one_more"}], built["tree"],
            built["joint_records"], built["actuators"])
    assert raised.value.reason == "too_many_observation_channels"


# -- the episode ------------------------------------------------------------

def test_an_episode_reads_the_command_it_issued_and_its_rate() -> None:
    """Before an action, the command in force; after it, the one just
    issued and its change per second. The first action reports no rate,
    and a command outside the box reads as the clamped one the drive got."""

    prepared = commanded()
    bundle = prepared["bundle"]
    interval = float(bundle["episode"]["control_interval_s"])
    high = float(bundle["actions"][0]["high"])
    asked = [[5.0, -3.0], [9.0, -1.0], [high + 50.0, 2.0], [0.0, 0.0]]
    seen: list[dict] = []

    def policy(step, observation):
        seen.append(dict(observation))
        return asked[step % len(asked)]

    episode = dyn.evaluate_episode(model(prepared), bundle, actions=policy)
    steps = episode["steps"]
    compiled = model(prepared)
    key = mujoco.mj_name2id(compiled, mujoco.mjtObj.mjOBJ_KEY,
                            bundle["episode"]["reset_keyframe"])
    reset = dyn.reset_command(compiled, bundle, key)

    assert seen[0]["shoulder_cmd"] == reset[0] and seen[0]["shoulder_cmd_rate"] == 0.0
    assert steps[0]["observation"]["shoulder_cmd"] == 5.0
    assert steps[0]["observation"]["shoulder_cmd_rate"] == 0.0
    assert seen[1]["shoulder_cmd"] == 5.0 and seen[1]["shoulder_cmd_rate"] == 0.0
    assert steps[1]["observation"]["shoulder_cmd_rate"] == pytest.approx(4.0 / interval)
    assert steps[1]["observation"]["elbow_cmd_rate"] == pytest.approx(2.0 / interval)
    assert seen[2]["shoulder_cmd_rate"] == pytest.approx(4.0 / interval)
    assert steps[2]["observation"]["shoulder_cmd"] == high
    assert steps[2]["observation"]["shoulder_cmd_rate"] == pytest.approx(
        (high - 9.0) / interval)
    # The action-rate term is paid on exactly those numbers.
    for row in steps[:4]:
        rate = row["observation"]
        assert row["reward_terms"][1]["value"] == pytest.approx(
            -((rate["shoulder_cmd_rate"] / 100) ** 2 + (rate["elbow_cmd_rate"] / 100) ** 2))


def test_a_played_policy_reads_its_previous_action(tmp_path) -> None:
    """A stored policy's input vector carries the command channels, so the
    engine can play a policy that reads its own last action."""

    prepared = commanded()
    bundle = prepared["bundle"]
    channels = dyn.policy_channels(bundle)
    assert channels[-2:] == ["shoulder_cmd", "shoulder_cmd_rate"]
    seen: list[dict] = []
    dyn.evaluate_episode(model(prepared), bundle,
                         actions=lambda step, obs: seen.append(obs) or [1.0, 1.0])
    assert all(set(channels) <= set(observation) for observation in seen)


@pytest.mark.parametrize("seed", [None, 5])
def test_a_stock_mujoco_reads_the_commands_the_engine_read(tmp_path: Path, seed) -> None:
    """The reference runner, with no Cadex on its path, computes the
    command channels from the bundle's words and scores the same action-rate
    reward, every number compared as text."""

    prepared = commanded(root=tmp_path)
    there = _stock(prepared["path"], seed)
    here = dyn.evaluate_episode(model(prepared), prepared["bundle"], seed=seed)

    assert there["cadex_importable"] is False
    assert there["total_reward"] == repr(here["total_reward"])
    rates = [abs(row["observation"]["shoulder_cmd_rate"]) for row in here["steps"]]
    assert max(rates) > 100.0
    for mine, yours in zip(here["steps"], there["steps"], strict=True):
        assert yours["observation"] == {
            name: repr(value) for name, value in mine["observation"].items()}


# -- the trainer ------------------------------------------------------------

def test_the_trainer_computes_the_engines_command_channels() -> None:
    numpy = pytest.importorskip("numpy")
    module = _trainer_module()
    bundle = commanded()["bundle"]

    assert module.channels(bundle) == dyn._task_channels(bundle)
    assert module.actor_channels(bundle) == dyn.policy_channels(bundle)
    assert module.command_channels(bundle) == dyn.command_channels(bundle)
    assert len(module.sensor_variance_floor(bundle)) == len(module.channels(bundle))
    issued, before = [7.5, -2.25], [1.0, 4.0]
    engine = dyn.command_values(bundle, issued, before)
    trained = module.command_vector(numpy, bundle, numpy.asarray(issued),
                                    numpy.asarray(before))
    assert trained.tolist() == [engine[name] for name in dyn.command_channels(bundle)]
    # Batched, as the rollout calls it.
    batch = module.command_vector(numpy, bundle, numpy.asarray([issued, before]),
                                  numpy.asarray([before, before]))
    assert batch.shape == (2, 4) and batch[1, 1] == 0.0
    source = inspect.getsource(module.train)
    assert "command_vector(jnp, task, *filter_carry)" in source
    assert "command_vector(jnp, task, clamped, replaced)" in source


def test_the_trainer_learns_a_policy_that_reads_its_previous_action(tmp_path) -> None:
    """End to end on the swing-up: the trainer writes a policy whose inputs
    end with the command channels, and the engine verifies and plays it."""

    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")
    task = {**pf.SWING_UP_TASK, "reward": pf.SWING_UP_TASK["reward"] + [
        {"label": "action_rate", "expression": "-(hinge_cmd_rate / 1000)**2",
         "weight": 0.01}]}
    observations = [*pf.SWING_UP_OBSERVATIONS,
                    {"kind": "command", "joint": "hinge", "motion_type": "angular",
                     "actuator_kind": "motor", "name": "hinge_cmd"}]
    prepared = pf.swing_up_bundle(task=task, observations=observations)
    assert prepared["bundle"]["commands"][0]["unit"] == "nmm"
    root = tmp_path / "project"
    (root / "outputs").mkdir(parents=True)
    (root / "outputs" / "job-model.xml").write_bytes(prepared["model_xml"])
    (root / "outputs" / "job-task.json").write_bytes(prepared["task_bytes"])
    out = tmp_path / "smooth.cxpolicy"
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment["CUDA_VISIBLE_DEVICES"] = ""
    result = subprocess.run(
        [python, "-P", str(TRAINER), str(root / "outputs" / "job-task.json"),
         "--out", str(out), "--seed", "0", "--iterations", "3", "--envs", "8",
         "--unroll", "10", "--quiet"],
        capture_output=True, text=True, env=environment, check=False,
    )
    assert result.returncode == 0, result.stderr[-4000:]
    container = dyn.decode_policy(out.read_bytes())
    assert container["header"]["observations"][-2:] == ["hinge_cmd", "hinge_cmd_rate"]
    evidence = dyn.verify_policy(container, prepared["bundle"],
                                 task_sha256=prepared["task_sha256"])
    assert evidence["witness_error"] < dyn.POLICY_WITNESS_TOLERANCE
    # The witnessed rows are landed observations: each command is the one
    # issued, so it lies in the action's box.
    limit = float(prepared["bundle"]["actions"][0]["high"])
    witnessed = container["header"]["evaluation"]["observations"]
    assert all(-limit <= row[-2] <= limit and math.isfinite(row[-1]) for row in witnessed)
    episode = dyn.evaluate_episode(
        prepared["model"], prepared["bundle"],
        actions=lambda step, obs: dyn.policy_forward(
            container["header"], container["weights"], obs, context="test"))
    assert episode["step_count"] > 0


# -- the surface ------------------------------------------------------------

def test_the_surface_offers_a_command_off_an_actuator_with_no_sensor() -> None:
    from test_dynamics_task_api import _api, _scene

    api = _api()
    scene = _scene(api)
    motor = scene["motor"]
    channel = api.observation(motor, "command", name="hip")
    assert channel.properties["kind"] == "command"
    assert channel.properties["actuator_kind"] == "motor"
    assert "grounded_sensor" not in channel.properties
    with pytest.raises(ValueError, match="actuator"):
        api.observation(scene["joints"][0], "command", name="hip")
    load = api.sensor(motor, "load_sensor", name="current", rate_hz=500,
                      resolution_nmm=1.0, noise_nmm=1.0)
    with pytest.raises(ValueError, match="sensor"):
        api.observation(motor, "command", name="hip", sensor=load)


def test_a_reward_may_sum_a_regulariser_over_every_drive_a_motion_may_not() -> None:
    """ADR-697: an action-rate term over 19 drives is 191 syntax nodes,
    which a reward accepts and the old 128-node cap refused. A motion
    formula keeps 128, because it is rendered back into Ondsel's syntax."""

    from test_dynamics_task_api import _api, _api_joint

    api = _api()
    nineteen = "-(" + " + ".join(f"(d{i}_rate/300)**2" for i in range(19)) + ")"
    assert api.reward(nineteen, weight=1.0e-3).properties["expression"] == nineteen
    assert api.termination(nineteen, below=-1.0e9).output_type == "termination"
    too_big = " + ".join(f"(d{i}_rate/300)**2" for i in range(60))
    with pytest.raises(ValueError, match="too complex"):
        api.reward(too_big)
    with pytest.raises(ValueError, match="too complex"):
        api.motion(_api_joint(api), " + ".join(["time*2"] * 30))


def test_describe_api_teaches_the_command_channel() -> None:
    from CadexScriptedRuntime import _capability_api_listing

    (observation,) = [entry for entry in _capability_api_listing()["assembly"]["exports"]
                      if entry["name"] == "observation"]
    assert "``command``" in observation["description"]
    assert "action rate" in observation["description"]
    assert "ADR-696" in observation["description"]
