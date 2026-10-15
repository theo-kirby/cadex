# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""An episode can start at a random phase of its gait reference (ADR-709).

Reference state initialisation (Peng et al. 2018): with
``api.task(reference_start="random")`` a seeded episode starts at a clip
sample drawn from its seed, in the clip's own pose and velocity there, with
the gait clock at that phase. The bundle's ``tracking`` section carries the
state at every sample; the engine, the trainer and the stock-MuJoCo runner
each draw a sample and read the clock from it, and they agree.
"""

from __future__ import annotations

import inspect
import json
import math
import random
from pathlib import Path

import pytest

import CadexDynamics as dyn

mujoco = pytest.importorskip("mujoco")
np = pytest.importorskip("numpy")

from test_dynamics_goal_model import _stock, model  # noqa: E402
from test_dynamics_policy_trainer import _trainer_module  # noqa: E402
from test_gait_task_reference import _api, _declared, _legged, _task, keyed  # noqa: E402,F401
from test_gait_tracking import _observed, _tracked  # noqa: E402

DEG = 180.0 / math.pi


@pytest.fixture(scope="module")
def started(keyed):  # noqa: F811
    compiled, home = keyed
    reference = dyn._reference_records(
        mujoco, compiled, _declared(stride_length_mm=300.0, start="random"),
        {"reset_keyframe": "solved"}, context="t")
    return compiled, home, reference


def test_the_script_surface_takes_a_random_start_only_with_a_reference() -> None:
    api = _api()
    parts, _spine, _legs, motor, model_value = _legged(api)
    trot = api.gait([parts[n] for n in ("lf", "rf", "lh", "rh")], gait="trot",
                    speed_mm_s=800)
    task = _task(api, model_value, motor, reference=trot, reference_start="random")
    assert task.properties["reference_start"] == "random"
    # phase 0 is the default and leaves the task the value it was
    assert "reference_start" not in _task(api, model_value, motor, reference=trot,
                                          reference_start="phase0").properties
    with pytest.raises(ValueError, match="declares none"):
        _task(api, model_value, motor, reference_start="random")
    with pytest.raises(ValueError, match="'phase0' or 'random'"):
        _task(api, model_value, motor, reference=trot, reference_start="middle")


def test_the_reference_carries_its_start_and_phase_zero_carries_nothing(keyed, started) -> None:  # noqa: F811
    compiled, _home = keyed
    plain = dyn._reference_records(mujoco, compiled, _declared(stride_length_mm=300.0),
                                   {"reset_keyframe": "solved"}, context="t")
    assert "start" not in plain
    assert started[2]["start"] == "random"
    tracking = dyn._tracking_records(plain, _observed(compiled, "hip_lf"),
                                     {"control_interval_s": 0.02}, taken=[], context="t")
    assert "start" not in tracking and "reset_qpos" not in tracking


def test_each_sample_is_the_clips_state_over_the_keyframes_ground_point(started) -> None:
    compiled, home, reference = started
    records = dyn._reference_start_records(mujoco, compiled, reference)
    assert records["start"] == "random"
    samples, dt = reference["samples"], reference["sample_dt_s"]
    speed = reference["parameters"]["speed_m_s"]
    clip = np.asarray(reference["qpos"])
    qpos, qvel = np.asarray(records["reset_qpos"]), np.asarray(records["reset_qvel"])
    assert qpos.shape == (samples, compiled.nq) and qvel.shape == (samples, compiled.nv)
    # where the keyframe stands, at the clip's height, attitude and joint angles
    assert np.allclose(qpos[:, :2], home[:2])
    assert np.allclose(qpos[:, 2:], clip[:, 2:])
    # the base moves at the reference's speed and the clip's own pitch rate
    assert np.allclose(qvel[:, 0], speed, atol=1e-9)
    assert np.allclose(qvel[:, 1], 0.0, atol=1e-9)
    pitch = np.radians(reference["body"]["pitch_deg"])
    rate = (np.roll(pitch, -1) - np.roll(pitch, 1)) / (2 * dt)
    assert np.allclose(qvel[:, 4], rate, atol=1e-6)
    # every joint's velocity is the clip's central difference, round the stride
    for name in reference["joints"]:
        joint = compiled.joint(name)
        angle = clip[:, compiled.jnt_qposadr[joint.id]]
        expected = (np.roll(angle, -1) - np.roll(angle, 1)) / (2 * dt)
        assert np.allclose(qvel[:, compiled.jnt_dofadr[joint.id]], expected, atol=1e-9), name
    # posed there, every foot the clip has down is on the floor it stood on
    data = mujoco.MjData(compiled)
    data.qpos[:] = home
    mujoco.mj_kinematics(compiled, data)
    floor = {s: data.geom_xpos[compiled.geom(f"pad_{s}").id][2] for s in ("lf", "rf", "lh", "rh")}
    for k in range(samples):
        data.qpos[:] = qpos[k]
        mujoco.mj_kinematics(compiled, data)
        for foot in ("LF", "RF", "LH", "RH"):
            if reference["contact"][foot][k]:
                pad = data.geom_xpos[compiled.geom(f"pad_{foot.lower()}").id][2]
                assert pad == pytest.approx(floor[foot.lower()], abs=2e-3)


def test_the_clock_reads_from_the_sample_it_started_at(started) -> None:
    compiled, _home, reference = started
    period = float(reference["parameters"]["period_s"])
    tracking = dyn._tracking_records(reference, _observed(compiled, "hip_lf"),
                                     {"control_interval_s": period / reference["samples"]},
                                     taken=[], context="t")
    task = {"tracking": tracking}
    for origin in (0, 3, reference["samples"] - 1):
        for step in range(2 * reference["samples"]):
            assert dyn.tracking_values(task, step, origin) == pytest.approx(
                dyn.tracking_values(task, step + origin), abs=1e-9)
    assert dyn.tracking_phase(tracking, 0, 3) == pytest.approx(3 / reference["samples"])


def test_a_reset_variation_adds_to_the_velocity_a_start_holds(keyed) -> None:  # noqa: F811
    compiled, _home = keyed
    data = mujoco.MjData(compiled)
    data.qvel[0], data.qvel[4] = 1.0, 0.25
    dyn._write_reset_variation(data, {"qpos_adr": 0, "qvel_adr": 0}, tilt_rad=0.0,
                               azimuth_rad=0.0, height_m=0.0,
                               angular_velocity_rad_s=(0.0, 0.5, 0.0),
                               linear_velocity_m_s=(0.5, 0.0, 0.0))
    assert data.qvel[0] == 1.5 and data.qvel[4] == 0.75


def _started_arm(tmp_path: Path):
    """ADR-706's tracked arm, starting at a random sample: each sample's state
    is the elbow at the reference's angle, moving at a stated rate."""

    prepared = _tracked(tmp_path)
    bundle = dict(prepared["bundle"])
    compiled = model(prepared)
    tracking = dict(bundle["tracking"])
    samples = int(tracking["samples"])
    elbow = next(compiled.jnt_qposadr[j] for j in range(compiled.njnt)
                 if "elbow" in compiled.joint(j).name)
    rows, rates = [], []
    for k in range(samples):
        row = [0.0] * compiled.nq
        row[elbow] = tracking["table"][k][0] / DEG
        rows.append(row)
        rate = [0.0] * compiled.nv
        rate[elbow] = 0.1 * k
        rates.append(rate)
    tracking.update(start="random", start_algorithm=dyn.REFERENCE_START_ALGORITHM,
                    reset_qpos=rows, reset_qvel=rates)
    bundle["tracking"] = tracking
    prepared["bundle"] = bundle
    prepared["path"].write_text(json.dumps(bundle, indent=2, sort_keys=True))
    return prepared, elbow


def test_a_seeded_episode_starts_at_its_drawn_sample_with_the_clock_there(tmp_path) -> None:
    prepared, elbow = _started_arm(tmp_path)
    bundle = prepared["bundle"]
    samples = int(bundle["tracking"]["samples"])
    starts = {}
    for seed in range(8):
        poses: list = []
        seen: list[dict] = []

        def still(step, observation, seen=seen):
            seen.append(dict(observation))
            return [0.0, 0.0]

        def first(step, data, final, action, poses=poses):
            if step == 0:
                poses.append((data.qpos.copy(), data.qvel.copy()))

        here = dyn.evaluate_episode(model(prepared), bundle, actions=still, sample=first,
                                    seed=seed)
        origin = here["reference_start"]
        # the draw continues the episode's stream after every other
        rng = random.Random(seed)
        dyn.apply_randomisation(mujoco, model(prepared), mujoco.MjData(model(prepared)),
                                bundle, rng=rng)
        dyn.draw_episode_variation(bundle, rng)
        assert origin == rng.randrange(samples)
        starts[seed] = origin
        qpos, qvel = poses[0]
        assert qpos[elbow] == pytest.approx(bundle["tracking"]["table"][origin][0] / DEG)
        assert qvel[elbow] == pytest.approx(0.1 * origin)
        assert seen[0]["ref_sin"] == pytest.approx(math.sin(2 * math.pi * origin / samples))
        for step, observation in enumerate(seen):
            for name, value in dyn.tracking_values(bundle, step, origin).items():
                assert observation[name] == value
        for row in here["steps"]:
            landed = dyn.tracking_values(bundle, row["step"] + 1, origin)
            assert {name: row["observation"][name] for name in landed} == landed
    assert len(set(starts.values())) > 1
    # unseeded, the episode starts at the keyframe and phase 0, as before
    nominal = dyn.evaluate_episode(model(prepared), bundle)
    assert "reference_start" not in nominal


def test_a_stock_mujoco_starts_where_the_engine_started(tmp_path) -> None:
    prepared, _elbow = _started_arm(tmp_path)
    for seed in (None, 5):
        there = _stock(prepared["path"], seed)
        here = dyn.evaluate_episode(model(prepared), prepared["bundle"], seed=seed)
        assert there["total_reward"] == repr(here["total_reward"])
        for mine, yours in zip(here["steps"], there["steps"], strict=True):
            assert yours["observation"] == {
                name: repr(value) for name, value in mine["observation"].items()}


def test_the_trainer_offsets_the_clock_by_each_environments_sample(tmp_path) -> None:
    module = _trainer_module()
    prepared, _elbow = _started_arm(tmp_path)
    bundle = prepared["bundle"]
    names = dyn.tracking_channels(bundle)
    steps = np.arange(0, 60)
    for origin in (0, 4, 12):
        trained = module.tracking_vector(np, bundle, steps, np.full(steps.shape, origin))
        for step in steps:
            engine = dyn.tracking_values(bundle, int(step), origin)
            assert trained[step].tolist() == pytest.approx(
                [engine[name] for name in names], abs=1e-9)
    source = (inspect.getsource(module.build_environment) + inspect.getsource(module.train))
    assert "tracking_vector(jnp, task, steps, origin)" in source
    assert "tracking_vector(jnp, task, steps + 1, origin)" in source
    assert 'task["tracking"]["reset_qpos"]' in source
    assert ".add(spin)" in source and ".set(spin)" not in source


def test_the_trainer_trains_from_random_starts_and_the_engine_verifies_it(tmp_path) -> None:
    """End to end: the real trainer carries a sample per environment and the
    engine verifies the policy it wrote against the same bundle."""

    import hashlib
    import os
    import subprocess

    from test_dynamics_policy_trainer import TRAINER, _venv_python

    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")
    prepared, _elbow = _started_arm(tmp_path)
    payload = prepared["path"].read_bytes()
    out = tmp_path / "started.cxpolicy"
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment["CUDA_VISIBLE_DEVICES"] = ""
    result = subprocess.run(
        [python, "-P", str(TRAINER), str(prepared["path"]), "--out", str(out),
         "--seed", "0", "--iterations", "3", "--envs", "8", "--unroll", "10", "--quiet"],
        capture_output=True, text=True, env=environment, check=False,
    )
    assert result.returncode == 0, result.stderr[-4000:]
    container = dyn.decode_policy(out.read_bytes())
    evidence = dyn.verify_policy(container, prepared["bundle"],
                                 task_sha256=hashlib.sha256(payload).hexdigest())
    assert evidence["witness_error"] < dyn.POLICY_WITNESS_TOLERANCE
