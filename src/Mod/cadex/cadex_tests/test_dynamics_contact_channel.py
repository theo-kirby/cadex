# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A task can say "foot down" (ADR-698).

A ``contact`` observation reads the normal force of every contact on one
component's collision shapes, in N, and a ``_down`` flag that is 1 while
that force is above the bundle's ``contact.down_above_n``. MuJoCo computes
it: a ``touch`` sensor on a box site the export draws around the shapes, so
the file carries it, MJX computes the same number, and the flag is one
comparison every evaluator writes -- the engine, the trainer and the
stock-MuJoCo reference reader. This file holds them to one rule.

The fixture is M9's free block on a floor: it rests there, so it is down
under its own weight, and a lift takes it off.
"""

from __future__ import annotations

import inspect
import os
from pathlib import Path
import subprocess

import pytest

import CadexDynamics as dyn
import dynamics_policy_fixtures as pf
import dynamics_task_episode as runner
from test_dynamics_policy_trainer import TRAINER, _trainer_module, _venv_python

mujoco = pytest.importorskip("mujoco")

CONTACT = {"kind": "contact", "component": "block", "name": "foot",
           "role": "privileged"}
#: A foot-contact reward: paid for being down, as a gait's contact schedule
#: would be, so the channel reaches a reward term by name.
CONTACT_TASK = {
    **pf.SHOVED_TASK,
    "reward": [*pf.SHOVED_TASK["reward"],
               {"label": "stance", "expression": "foot_down", "weight": 0.5}],
}


def contact_bundle(observations=(CONTACT,), *, task=CONTACT_TASK):
    built = pf.shoved_built()
    records = dyn.observation_records(
        [*pf.SHOVED_OBSERVATIONS, *observations], built["tree"],
        built["joint_records"], built["actuators"])
    exported = dyn.export_mjcf(built, observations=records)
    reloaded = dyn.load_model(exported["xml"])
    bundle = dyn.task_records(built, reloaded, dict(task), observations=records)
    return {"built": built, "xml": exported["xml"], "model": reloaded,
            "bundle": bundle, "evidence": exported["evidence"]}


def _settled(model, bundle, *, lift_mm: float = 0.0, steps: int = 400):
    data = mujoco.MjData(model)
    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY,
                            bundle["episode"]["reset_keyframe"])
    mujoco.mj_resetDataKeyframe(model, data, key)
    for _ in range(steps):
        mujoco.mj_step(model, data)
    data.qpos[2] += lift_mm / 1000.0
    data.qvel[:] = 0.0
    mujoco.mj_forward(model, data)
    return data


def _block_weight_n(model) -> float:
    body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "block")
    return float(model.body_subtreemass[body]) * float(-model.opt.gravity[2])


# -- the bundle -------------------------------------------------------------

def test_a_contact_is_a_touch_sensor_on_a_volume_drawn_round_the_shapes() -> None:
    prepared = contact_bundle()
    bundle, compiled = prepared["bundle"], prepared["model"]
    (row,) = [row for row in bundle["observations"] if row["kind"] == "contact"]

    assert row["channels"] == ["foot", "foot_down"]
    assert row["unit"] == "n" and row["scale"] == 1.0 and row["dim"] == 1
    assert row["contact"] == {"body": "block", "down_above_n": 0.0}
    assert row["role"] == "privileged"
    assert dyn._task_channels(bundle)[-2:] == ["foot", "foot_down"]
    assert "foot_down" not in dyn.policy_channels(bundle)

    sensor = mujoco.mj_name2id(compiled, mujoco.mjtObj.mjOBJ_SENSOR, row["sensor"])
    assert compiled.sensor_type[sensor] == mujoco.mjtSensor.mjSENS_TOUCH
    site = int(compiled.sensor_objid[sensor])
    assert compiled.site_bodyid[site] == mujoco.mj_name2id(
        compiled, mujoco.mjtObj.mjOBJ_BODY, "block")
    # The block's one shape is a 120 x 60 x 40 mm box: its bounding sphere,
    # radius half the diagonal, bounds the volume on every axis.
    radius = (0.120 ** 2 + 0.060 ** 2 + 0.040 ** 2) ** 0.5 / 2.0
    assert compiled.site_size[site].tolist() == pytest.approx([radius] * 3)
    assert compiled.site_rgba[site][3] == 0.0
    # The export is verified with its one extra site, and adds nothing else.
    plain = contact_bundle(observations=(), task=pf.SHOVED_TASK)["model"]
    assert compiled.nsite == plain.nsite + 1
    assert compiled.ngeom == plain.ngeom and compiled.nbody == plain.nbody


def test_a_task_without_a_contact_keeps_its_bytes() -> None:
    bundle = pf.shoved_bundle()["bundle"]
    assert not any("contact" in row for row in bundle["observations"])
    assert "foot" not in dyn._task_channels(bundle)


def test_a_component_that_cannot_touch_anything_is_refused() -> None:
    with pytest.raises(dyn.DynamicsError) as raised:
        contact_bundle(observations=(
            {"kind": "contact", "component": "flap", "name": "flap_touch",
             "role": "privileged"},))
    assert raised.value.reason == "observation_contact_no_collision"
    assert raised.value.observed == {"component": "flap"}


def test_a_contact_names_two_channels_and_they_clash_like_any() -> None:
    with pytest.raises(dyn.DynamicsError) as raised:
        contact_bundle(observations=(
            CONTACT, {"kind": "position", "joint": "wrist",
                      "motion_type": "angular", "name": "foot_down"}))
    assert raised.value.reason == "duplicate_observation_channel"


# -- the reading ------------------------------------------------------------

def test_a_resting_block_is_down_under_its_weight_and_a_lifted_one_is_not() -> None:
    prepared = contact_bundle()
    compiled, bundle = prepared["model"], prepared["bundle"]

    resting = dyn.observation_values(bundle, _settled(compiled, bundle).sensordata)
    assert resting["foot"] == pytest.approx(_block_weight_n(compiled), rel=0.02)
    assert resting["foot_down"] == 1.0

    lifted = dyn.observation_values(
        bundle, _settled(compiled, bundle, lift_mm=20.0).sensordata)
    assert lifted["foot"] == 0.0 and lifted["foot_down"] == 0.0


def test_an_episode_pays_a_reward_on_the_down_flag() -> None:
    prepared = contact_bundle()
    episode = dyn.evaluate_episode(prepared["model"], prepared["bundle"],
                                   actions=lambda step, obs: [0.0])
    rows = episode["steps"]
    assert any(row["observation"]["foot_down"] == 1.0 for row in rows)
    for row in rows:
        stance = [term for term in row["reward_terms"] if term["label"] == "stance"]
        assert stance[0]["value"] == row["observation"]["foot_down"]


def test_every_reader_derives_the_same_flag() -> None:
    """The engine, the stock-MuJoCo reference reader and the trainer agree
    on the flag, in contact, off it, and exactly at the threshold."""

    numpy = pytest.importorskip("numpy")
    module = _trainer_module()
    prepared = contact_bundle()
    compiled, bundle = prepared["model"], prepared["bundle"]
    (row,) = [row for row in bundle["observations"] if row["kind"] == "contact"]
    for lift in (0.0, 20.0):
        data = _settled(compiled, bundle, lift_mm=lift)
        assert runner.observation_values(bundle, data.sensordata) == \
            dyn.observation_values(bundle, data.sensordata)
    for force in (0.0, 1.0e-9, 12.5):
        engine = dyn.contact_reading(force, row["contact"])
        trained = module.contact_reading(
            numpy, numpy.asarray([force], dtype=numpy.float32), row["contact"])
        assert trained.tolist() == pytest.approx(engine)
    assert dyn.contact_reading(0.0, row["contact"]) == [0.0, 0.0]

    assert module.channels(bundle) == dyn._task_channels(bundle)
    floor = module.sensor_variance_floor(bundle)
    assert len(floor) == len(module.channels(bundle))
    names = module.channels(bundle)
    assert floor[names.index("foot")] == 0.0
    assert floor[names.index("foot_down")] == 0.25
    source = inspect.getsource(module.train)
    assert 'contact_reading(jnp, segment, record["contact"])' in source


# -- the trainer, MJX -------------------------------------------------------

def test_mjx_reads_the_contact_the_engine_reads() -> None:
    """MJX computes the touch sensor from its own contacts; it has to agree
    with MuJoCo's on the file the trainer loads."""

    mjx = pytest.importorskip("mujoco.mjx")
    jax = pytest.importorskip("jax")
    prepared = contact_bundle()
    compiled, bundle = prepared["model"], prepared["bundle"]
    (row,) = [row for row in bundle["observations"] if row["kind"] == "contact"]
    for lift in (0.0, 20.0):
        data = _settled(compiled, bundle, lift_mm=lift)
        stepped = mjx.forward(mjx.put_model(compiled), mjx.put_data(compiled, data))
        here = float(data.sensordata[row["adr"]])
        there = float(jax.device_get(stepped.sensordata)[row["adr"]])
        assert there == pytest.approx(here, rel=1.0e-3, abs=1.0e-3)


def test_the_trainer_trains_a_task_that_reads_foot_contact(tmp_path) -> None:
    """End to end: the trainer reads the contact from MJX's sensordata,
    derives the flag, pays the reward on it, and the engine verifies the
    policy against the same bundle."""

    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")
    import hashlib
    import json

    prepared = contact_bundle()
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
    out = tmp_path / "contact.cxpolicy"
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
    assert "foot_down" not in container["header"]["observations"]
    evidence = dyn.verify_policy(container, bundle,
                                 task_sha256=hashlib.sha256(payload).hexdigest())
    assert evidence["witness_error"] < dyn.POLICY_WITNESS_TOLERANCE


# -- the surface ------------------------------------------------------------

def test_the_surface_offers_contact_on_a_component() -> None:
    from test_dynamics_task_api import _api, _scene

    api = _api()
    scene = _scene(api)
    channel = api.observation(scene["components"][1], "contact", name="paw",
                              role="privileged")
    assert channel.properties["kind"] == "contact"
    with pytest.raises(ValueError):
        api.observation(scene["motor"], "contact", name="paw")


def test_describe_api_teaches_the_contact_channel() -> None:
    from CadexScriptedRuntime import _capability_api_listing

    (observation,) = [entry for entry in _capability_api_listing()["assembly"]["exports"]
                      if entry["name"] == "observation"]
    assert "``contact``" in observation["description"]
    assert "ADR-698" in observation["description"]
