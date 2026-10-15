# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A task can say "smooth" in joint accelerations (ADR-699).

An ``acceleration`` observation reads one joint coordinate's ``qacc`` after
the control step, in deg/s^2 or mm/s^2. MuJoCo has no sensor for it, so the
bundle states it in an ``accelerations`` section -- the degree of freedom
and the scale -- and every evaluator reads the simulator's own field: the
engine, the trainer (MJX's ``qacc``) and the stock-MuJoCo reference runner.
It is privileged, and nothing else.

With it the standard locomotion regularisers are all reward terms: the
action rate (ADR-696), the joint acceleration (here), the torque and the
mechanical power (``actuator_force`` and ``velocity``), and the foot slip
(ADR-698's ``_down`` times a foot speed). :data:`REGULARISED_TASK` writes
every one of them, and a test holds each term to its formula.
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
from test_dynamics_command_channel import SWEPT
from test_dynamics_contact_channel import CONTACT, contact_bundle
from test_dynamics_goal_model import ARM_OBSERVATIONS, ARM_TASK, _stock, made, model
from test_dynamics_policy_trainer import TRAINER, _trainer_module, _venv_python

mujoco = pytest.importorskip("mujoco")

ACCELERATED = [
    *ARM_OBSERVATIONS,
    {"kind": "acceleration", "joint": "shoulder", "motion_type": "angular",
     "name": "shoulder_acc", "role": "privileged"},
    {"kind": "acceleration", "joint": "elbow", "motion_type": "angular",
     "name": "elbow_acc", "role": "privileged"},
]
ACC_TASK = {
    **{key: value for key, value in ARM_TASK.items() if key != "goal"},
    "reward": [
        {"label": "up", "expression": "hand_z", "weight": 1.0e-3},
        {"label": "joint_acc",
         "expression": "-((shoulder_acc / 10000)**2 + (elbow_acc / 10000)**2)",
         "weight": 0.1},
    ],
}


def accelerated(**overrides):
    return made(ACC_TASK, motors=SWEPT, observations=ACCELERATED, **overrides)


#: The block on the floor, its wrist driven, observed for every standard
#: regulariser: the torque and the joint speed of the wrist, its
#: acceleration, the block's own ground speed, and whether it is down.
REGULARISERS = [
    CONTACT,
    {"kind": "velocity", "joint": "wrist", "motion_type": "angular",
     "name": "wrist_vel"},
    {"kind": "actuator_force", "joint": "wrist", "motion_type": "angular",
     "actuator_kind": "motor", "name": "wrist_tau", "role": "privileged"},
    {"kind": "acceleration", "joint": "wrist", "motion_type": "angular",
     "name": "wrist_acc", "role": "privileged"},
    {"kind": "command", "joint": "wrist", "motion_type": "angular",
     "actuator_kind": "motor", "name": "wrist_cmd", "role": "privileged"},
]
#: The example task: every standard locomotion regulariser as a reward term.
REGULARISED_TASK = {
    **pf.SHOVED_TASK,
    "reward": [
        *pf.SHOVED_TASK["reward"],
        {"label": "action_rate", "expression": "-(wrist_cmd_rate / 1000)**2",
         "weight": 0.01},
        {"label": "joint_acc", "expression": "-(wrist_acc / 10000)**2",
         "weight": 0.01},
        {"label": "torque", "expression": "-(wrist_tau / 500)**2", "weight": 0.01},
        # Mechanical power in W: N*mm times deg/s, times pi/180 and 1/1000.
        {"label": "power",
         "expression": "-abs(wrist_tau * wrist_vel) * 1.7453292519943295e-05",
         "weight": 0.01},
        # Foot slip: the ground speed of a foot that is down.
        {"label": "slip",
         "expression": "-sqrt(drift_x**2 + drift_y**2) * foot_down / 1000",
         "weight": 0.1},
    ],
}


# -- the bundle -------------------------------------------------------------

def test_an_acceleration_is_a_row_of_its_own_and_carries_no_sensor() -> None:
    prepared = accelerated()
    bundle, compiled = prepared["bundle"], model(prepared)
    plain = made(ACC_TASK | {"reward": ACC_TASK["reward"][:1]}, motors=SWEPT)

    rows = bundle["accelerations"]
    assert [row["channels"] for row in rows] == [["shoulder_acc"], ["elbow_acc"]]
    for row in rows:
        assert row["unit"] == "deg/s^2" and row["role"] == "privileged"
        assert row["scale"] == pytest.approx(180.0 / math.pi)
        joint = mujoco.mj_name2id(compiled, mujoco.mjtObj.mjOBJ_JOINT, row["joint"])
        assert row["dof"] == int(compiled.jnt_dofadr[joint])
    assert compiled.nsensor == model(plain).nsensor
    assert not any(row["kind"] == "acceleration" for row in bundle["observations"])
    assert dyn._task_channels(bundle)[-2:] == ["shoulder_acc", "elbow_acc"]
    assert not set(dyn.policy_channels(bundle)) & {"shoulder_acc", "elbow_acc"}
    assert "accelerations" not in plain["bundle"]


def test_an_acceleration_for_the_policy_is_refused() -> None:
    with pytest.raises(dyn.DynamicsError) as raised:
        made(ACC_TASK, motors=SWEPT, observations=[
            *ARM_OBSERVATIONS,
            {"kind": "acceleration", "joint": "shoulder", "motion_type": "angular",
             "name": "shoulder_acc"}])
    assert raised.value.reason == "acceleration_not_privileged"


def test_an_acceleration_names_a_channel_that_clashes_like_any() -> None:
    with pytest.raises(dyn.DynamicsError) as raised:
        made(ACC_TASK, motors=SWEPT, observations=[
            *ACCELERATED,
            {"kind": "velocity", "joint": "elbow", "motion_type": "angular",
             "name": "elbow_acc"}])
    assert raised.value.reason == "duplicate_observation_channel"


# -- the reading ------------------------------------------------------------

def test_an_episode_reads_qacc_and_pays_the_regulariser_on_it() -> None:
    prepared = accelerated()
    compiled, bundle = model(prepared), prepared["bundle"]
    data = mujoco.MjData(compiled)

    def act(step, observation):
        return [20.0 * math.sin(0.4 * step), -15.0 * math.cos(0.3 * step)]

    episode = dyn.evaluate_episode(compiled, bundle, actions=act)
    rows = episode["steps"]
    assert max(abs(row["observation"]["shoulder_acc"]) for row in rows) > 100.0
    for row in rows:
        obs = row["observation"]
        (term,) = [t for t in row["reward_terms"] if t["label"] == "joint_acc"]
        assert term["value"] == pytest.approx(
            -((obs["shoulder_acc"] / 1e4) ** 2 + (obs["elbow_acc"] / 1e4) ** 2))
    # The reading is the field times the scale, nothing else.
    data.qacc[:] = [0.5 * (index + 1) for index in range(compiled.nv)]
    values = dyn.acceleration_values(bundle, data.qacc)
    for row in bundle["accelerations"]:
        assert values[row["channels"][0]] == pytest.approx(
            data.qacc[row["dof"]] * 180.0 / math.pi)


@pytest.mark.parametrize("seed", [None, 5])
def test_a_stock_mujoco_reads_the_accelerations_the_engine_read(tmp_path: Path, seed) -> None:
    prepared = accelerated(root=tmp_path)
    there = _stock(prepared["path"], seed)
    here = dyn.evaluate_episode(model(prepared), prepared["bundle"], seed=seed)

    assert there["cadex_importable"] is False
    assert there["total_reward"] == repr(here["total_reward"])
    for mine, yours in zip(here["steps"], there["steps"], strict=True):
        assert yours["observation"] == {
            name: repr(value) for name, value in mine["observation"].items()}


def test_every_standard_regulariser_is_a_reward_term() -> None:
    """The example task: action rate, joint acceleration, torque, power and
    foot slip, each term equal to its formula on the landed observation."""

    prepared = contact_bundle(observations=REGULARISERS, task=REGULARISED_TASK)
    bundle = prepared["bundle"]
    episode = dyn.evaluate_episode(
        prepared["model"], bundle,
        actions=lambda step, obs: [400.0 * math.sin(0.5 * step)])
    rows = episode["steps"]
    formulas = {
        "action_rate": lambda o: -(o["wrist_cmd_rate"] / 1000) ** 2,
        "joint_acc": lambda o: -(o["wrist_acc"] / 10000) ** 2,
        "torque": lambda o: -(o["wrist_tau"] / 500) ** 2,
        "power": lambda o: -abs(o["wrist_tau"] * o["wrist_vel"]) * math.pi / 180 / 1000,
        "slip": lambda o: -math.hypot(o["drift_x"], o["drift_y"]) * o["foot_down"] / 1000,
    }
    for row in rows:
        terms = {term["label"]: term["value"] for term in row["reward_terms"]}
        for label, formula in formulas.items():
            assert terms[label] == pytest.approx(formula(row["observation"]), abs=1e-12)
    # Every term is live on this episode: the wrist moves and the block
    # slides while it is down.
    for label in formulas:
        assert any(term["value"] != 0.0 for row in rows
                   for term in row["reward_terms"] if term["label"] == label), label


# -- the trainer ------------------------------------------------------------

def test_the_trainer_computes_the_engines_acceleration_channels() -> None:
    numpy = pytest.importorskip("numpy")
    module = _trainer_module()
    bundle = accelerated()["bundle"]

    assert module.channels(bundle) == dyn._task_channels(bundle)
    assert module.actor_channels(bundle) == dyn.policy_channels(bundle)
    assert module.acceleration_channels(bundle) == dyn.acceleration_channels(bundle)
    assert len(module.sensor_variance_floor(bundle)) == len(module.channels(bundle))
    qacc = numpy.linspace(-2.0, 3.0, model(accelerated()).nv)
    engine = dyn.acceleration_values(bundle, qacc)
    trained = module.acceleration_vector(numpy, bundle, qacc)
    assert trained.tolist() == pytest.approx(
        [engine[name] for name in dyn.acceleration_channels(bundle)])
    batch = module.acceleration_vector(numpy, bundle, numpy.stack([qacc, 2.0 * qacc]))
    assert batch.shape == (2, 2)
    assert batch[1].tolist() == pytest.approx((2.0 * trained).tolist())
    source = inspect.getsource(module.build_environment) + inspect.getsource(module.train)
    assert "acceleration_vector(jnp, task, data.qacc)" in source


def test_mjx_steps_to_the_qacc_the_engine_steps_to() -> None:
    """The trainer reads MJX's ``qacc`` after a step; it has to agree with
    MuJoCo's on the file the trainer loads."""

    mjx = pytest.importorskip("mujoco.mjx")
    jax = pytest.importorskip("jax")
    prepared = accelerated()
    compiled, bundle = model(prepared), prepared["bundle"]
    data = mujoco.MjData(compiled)
    key = mujoco.mj_name2id(compiled, mujoco.mjtObj.mjOBJ_KEY,
                            bundle["episode"]["reset_keyframe"])
    mujoco.mj_resetDataKeyframe(compiled, data, key)
    data.ctrl[:] = [0.3, -0.2][: compiled.nu]
    mujoco.mj_forward(compiled, data)
    stepped = mjx.step(mjx.put_model(compiled), mjx.put_data(compiled, data))
    mujoco.mj_step(compiled, data)
    here = dyn.acceleration_values(bundle, data.qacc)
    there = dyn.acceleration_values(bundle, jax.device_get(stepped.qacc))
    for name, value in here.items():
        assert there[name] == pytest.approx(value, rel=2.0e-3, abs=1.0e-2)


def test_the_trainer_trains_a_task_with_every_regulariser(tmp_path) -> None:
    """End to end: the example task, trained by the real trainer, and the
    policy verified by the engine against the same bundle."""

    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")
    import hashlib
    import json

    prepared = contact_bundle(observations=REGULARISERS, task=REGULARISED_TASK)
    bundle = dict(prepared["bundle"])
    bundle["model"] = {"path": "outputs/job-model.xml", "output": "job_model",
                       "bytes": len(prepared["xml"]),
                       "sha256": hashlib.sha256(prepared["xml"]).hexdigest(),
                       "mujoco_version": str(bundle["mujoco_version"])}
    payload = json.dumps(bundle, indent=2, sort_keys=True).encode("utf-8")
    root = tmp_path / "project"
    (root / "outputs").mkdir(parents=True)
    (root / "outputs" / "job-model.xml").write_bytes(prepared["xml"])
    (root / "outputs" / "job-task.json").write_bytes(payload)
    out = tmp_path / "regularised.cxpolicy"
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
    assert "wrist_acc" not in container["header"]["observations"]
    evidence = dyn.verify_policy(container, bundle,
                                 task_sha256=hashlib.sha256(payload).hexdigest())
    assert evidence["witness_error"] < dyn.POLICY_WITNESS_TOLERANCE


# -- the surface ------------------------------------------------------------

def test_the_surface_offers_an_acceleration_on_a_joint() -> None:
    from test_dynamics_task_api import _api, _scene

    api = _api()
    scene = _scene(api)
    joint = scene["joints"][0]
    channel = api.observation(joint, "acceleration", name="hip_acc",
                              role="privileged")
    assert channel.properties["kind"] == "acceleration"
    with pytest.raises(ValueError):
        api.observation(scene["components"][1], "acceleration", name="hip_acc")


def test_describe_api_teaches_the_acceleration_channel() -> None:
    from CadexScriptedRuntime import _capability_api_listing

    (observation,) = [entry for entry in _capability_api_listing()["assembly"]["exports"]
                      if entry["name"] == "observation"]
    assert "``acceleration``" in observation["description"]
    assert "ADR-699" in observation["description"]
