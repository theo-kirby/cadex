# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""A task's gait reference reads as channels on its gait clock (ADR-706).

A task that declares a reference (ADR-703) gains a ``tracking`` section and
its channels, after every other: ``ref_sin`` and ``ref_cos``, the clock,
which the policy reads; then, for the reward and the critic, ``<name>_ref``
for each position observation of a joint the clip poses, and each foot's
``ref_<foot>_lift`` and ``ref_<foot>_down``. A tracking reward is then an
expression: ``exp(-((q_knee - q_knee_ref) / 15)^2)``.

The claims are checked against the clip itself: on a clock that turns one
sample a step, step ``k`` reads sample ``k``; between samples it reads
linearly; it comes round after a stride. Three evaluators compute it -- the
engine, the trainer and the stock-MuJoCo runner -- and they agree.
"""

from __future__ import annotations

import inspect
import json
import math
from pathlib import Path

import pytest

import CadexDynamics as dyn

mujoco = pytest.importorskip("mujoco")
np = pytest.importorskip("numpy")

from test_dynamics_goal_model import ARM_TASK, _stock, made, model  # noqa: E402
from test_dynamics_policy_trainer import _trainer_module  # noqa: E402
from test_gait_task_reference import _declared, keyed  # noqa: E402,F401

DEG = 180.0 / math.pi


def _observed(compiled, *joints: str) -> list[dict]:
    """Position observations of ``joints``, a velocity of the first, and a
    position of a joint the clip does not pose -- as task_records sees them."""

    rows = [{"kind": "position", "object_name": joint, "scale": DEG,
             "channels": [f"q_{joint}"]} for joint in joints]
    rows.append({"kind": "velocity", "object_name": joints[0], "scale": DEG,
                 "channels": [f"dq_{joints[0]}"]})
    rows.append({"kind": "position", "object_name": "root", "scale": DEG,
                 "channels": ["q_root"]})
    return rows


@pytest.fixture(scope="module")
def clip(keyed):  # noqa: F811
    compiled, _home = keyed
    return compiled, dyn._reference_records(
        mujoco, compiled, _declared(stride_length_mm=300.0),
        {"reset_keyframe": "solved"}, context="t")


def _tracking(clip_record, observations, *, steps_per_sample: float = 1.0):
    """A tracking section whose clock turns one sample every
    ``steps_per_sample`` control steps."""

    period = float(clip_record["parameters"]["period_s"])
    interval = period / (int(clip_record["samples"]) * steps_per_sample)
    return dyn._tracking_records(clip_record, observations,
                                 {"control_interval_s": interval},
                                 taken=["q_hip_lf"], context="t")


def test_the_reference_reads_as_named_channels(clip) -> None:
    compiled, reference = clip
    tracking = _tracking(reference, _observed(compiled, "hip_lf", "knee_rh"))
    assert tracking["channels"] == [
        "ref_sin", "ref_cos", "q_hip_lf_ref", "q_knee_rh_ref",
        "ref_lf_lift", "ref_rf_lift", "ref_lh_lift", "ref_rh_lift",
        "ref_lf_down", "ref_rf_down", "ref_lh_down", "ref_rh_down",
    ]
    assert tracking["policy_channels"] == ["ref_sin", "ref_cos"]
    # the names a reward is first compiled against cover the exact ones
    assert set(tracking["channels"]) <= set(
        dyn._tracking_candidates(_observed(compiled, "hip_lf", "knee_rh")))
    assert tracking["held"] == [False] * 6 + [True] * 4
    assert len(tracking["table"]) == reference["samples"]
    hip = reference["joints"].index("hip_lf")
    for k, row in enumerate(tracking["table"]):
        assert row[0] == pytest.approx(DEG * reference["joint_angles_rad"][k][hip])
        for column, foot in enumerate(("LF", "RF", "LH", "RH")):
            assert row[6 + column] == float(reference["contact"][foot][k])
            # a foot that is down is on its own floor; a swinging one is above it
            if reference["contact"][foot][k]:
                assert row[2 + column] == pytest.approx(0.0, abs=1e-6)
    lifts = np.asarray(tracking["table"])[:, 2:6]
    assert lifts.min() == pytest.approx(0.0)
    # the swing peaks between two samples, so the sampled peak is just under it
    swing = 1000.0 * reference["parameters"]["swing_height_m"]
    assert 0.95 * swing < lifts.max() <= swing + 1e-6


def test_the_clock_reads_the_clip_on_its_samples_between_them_and_round(clip) -> None:
    compiled, reference = clip
    tracking = _tracking(reference, _observed(compiled, "hip_lf"))
    task = {"tracking": tracking}
    samples = reference["samples"]
    names = tracking["channels"]
    for k in range(samples):
        values = dyn.tracking_values(task, k)
        assert [values[name] for name in names[2:]] == pytest.approx(tracking["table"][k])
        assert values["ref_sin"] == pytest.approx(math.sin(2 * math.pi * k / samples), abs=1e-9)
        assert values["ref_cos"] == pytest.approx(math.cos(2 * math.pi * k / samples), abs=1e-9)
        # one stride on, the same pose
        later = dyn.tracking_values(task, k + samples)
        assert [later[name] for name in names] == pytest.approx([values[name] for name in names])
    # at half a sample per step, an odd step is midway between two samples
    halved = {"tracking": _tracking(reference, _observed(compiled, "hip_lf"),
                                    steps_per_sample=2.0)}
    table = tracking["table"]
    for k in range(samples):
        mid = dyn.tracking_values(halved, 2 * k + 1)
        after = table[(k + 1) % samples]
        assert mid["q_hip_lf_ref"] == pytest.approx(0.5 * (table[k][0] + after[0]))
        assert mid["ref_lh_lift"] == pytest.approx(0.5 * (table[k][3] + after[3]))
        # a foot down on either side of the midpoint reads down
        assert mid["ref_lh_down"] == (1.0 if table[k][7] + after[7] >= 1.0 else 0.0)


def test_a_reference_channel_that_takes_a_taken_name_is_refused(clip) -> None:
    compiled, reference = clip
    with pytest.raises(dyn.DynamicsError) as raised:
        dyn._tracking_records(reference, _observed(compiled, "hip_lf"),
                              {"control_interval_s": 0.02},
                              taken=["q_hip_lf", "ref_sin", "q_hip_lf_ref"], context="t")
    assert raised.value.reason == "tracking_channel_clash"
    assert raised.value.observed == {"channels": ["q_hip_lf_ref", "ref_sin"]}


def _arm_tracking(prepared) -> dict:
    """A tracking section on the arm's elbow: one swing of 40 degrees over a
    13-sample stride, a contact square wave, at a clock that is not a whole
    number of steps a sample."""

    compiled = model(prepared)
    elbow = next(compiled.joint(j).name for j in range(compiled.njnt)
                 if "elbow" in compiled.joint(j).name)
    samples = 13
    reference = {
        "samples": samples, "joints": [elbow],
        "joint_angles_rad": [[math.radians(40.0) * math.sin(2 * math.pi * k / samples)]
                             for k in range(samples)],
        "foot_positions_m": {"LF": [[0.0, 0.0, 0.01 * (k % 5)] for k in range(samples)]},
        "contact": {"LF": [k < 7 for k in range(samples)]},
        "parameters": {"period_s": 0.37},
    }
    observations = [{"kind": "position", "object_name": elbow, "scale": DEG,
                     "channels": ["elbow_angle"]}]
    return dyn._tracking_records(reference, observations, prepared["bundle"]["episode"],
                                 taken=dyn._task_channels(prepared["bundle"]), context="t")


TRACKED_REWARD = [
    {"label": "pose", "expression": "exp(-((elbow_angle - elbow_angle_ref) / 15)**2)",
     "weight": 1.0},
    {"label": "clock", "expression": "ref_sin * ref_lf_down + ref_cos * ref_lf_lift / 40",
     "weight": 0.5},
]


def _tracked(tmp_path: Path):
    plain = {**{key: value for key, value in ARM_TASK.items() if key != "goal"},
             "reward": [{"label": "up", "expression": "hand_z", "weight": 1.0e-3}]}
    prepared = made(plain, root=tmp_path)
    bundle = dict(prepared["bundle"])
    bundle["tracking"] = _arm_tracking(prepared)
    bundle["reward"] = list(bundle["reward"]) + TRACKED_REWARD
    prepared["bundle"] = bundle
    prepared["path"].write_text(json.dumps(bundle, indent=2, sort_keys=True))
    return prepared


def test_an_episode_scores_where_a_step_lands_against_the_reference_then(tmp_path) -> None:
    prepared = _tracked(tmp_path)
    bundle = prepared["bundle"]
    assert dyn._task_channels(bundle)[-5:] == [
        "ref_sin", "ref_cos", "elbow_angle_ref", "ref_lf_lift", "ref_lf_down"]
    assert dyn.policy_channels(bundle)[-2:] == ["ref_sin", "ref_cos"]
    assert "elbow_angle_ref" not in dyn.policy_channels(bundle)
    seen: list[dict] = []

    def still(step, observation):
        seen.append(dict(observation))
        return [0.0, 0.0]

    here = dyn.evaluate_episode(model(prepared), bundle, actions=still)
    for step, observation in enumerate(seen):
        for name, value in dyn.tracking_values(bundle, step).items():
            assert observation[name] == value
    for row in here["steps"]:
        landed = dyn.tracking_values(bundle, row["step"] + 1)
        assert {name: row["observation"][name] for name in landed} == landed
        terms = {term["label"]: term["value"] for term in row["reward_terms"]}
        o = row["observation"]
        assert terms["pose"] == pytest.approx(
            math.exp(-((o["elbow_angle"] - o["elbow_angle_ref"]) / 15) ** 2))
    # the clock is live: the reference moves and the foot lifts and lands
    assert len({row["observation"]["ref_lf_down"] for row in here["steps"]}) == 2
    assert len({round(row["observation"]["elbow_angle_ref"], 6) for row in here["steps"]}) > 13


def test_a_stock_mujoco_reads_the_reference_the_engine_reads(tmp_path) -> None:
    prepared = _tracked(tmp_path)
    there = _stock(prepared["path"])
    here = dyn.evaluate_episode(model(prepared), prepared["bundle"])
    assert there["cadex_importable"] is False
    assert there["total_reward"] == repr(here["total_reward"])
    for mine, yours in zip(here["steps"], there["steps"], strict=True):
        assert yours["observation"] == {
            name: repr(value) for name, value in mine["observation"].items()}


def test_the_trainer_computes_the_engines_reference(tmp_path) -> None:
    module = _trainer_module()
    bundle = _tracked(tmp_path)["bundle"]
    assert module.channels(bundle) == dyn._task_channels(bundle)
    assert module.actor_channels(bundle) == dyn.policy_channels(bundle)
    assert module.tracking_channels(bundle) == dyn.tracking_channels(bundle)
    assert len(module.sensor_variance_floor(bundle)) == len(module.channels(bundle))
    steps = np.arange(0, 120)
    trained = module.tracking_vector(np, bundle, steps)
    assert trained.shape == (120, len(dyn.tracking_channels(bundle)))
    for step in steps:
        engine = dyn.tracking_values(bundle, int(step))
        assert trained[step].tolist() == pytest.approx(
            [engine[name] for name in dyn.tracking_channels(bundle)], abs=1e-9)
    source = (inspect.getsource(module.build_environment) + inspect.getsource(module.train))
    assert "tracking_vector(jnp, task, steps, origin)" in source
    assert "tracking_vector(jnp, task, steps + 1, origin)" in source


def test_the_trainer_trains_a_tracking_task_and_the_engine_verifies_it(tmp_path) -> None:
    """End to end: the real trainer builds the graph with the clock in the
    actor and the landed reference in the reward, and the engine verifies
    the policy it wrote against the same bundle."""

    import hashlib
    import os
    import subprocess

    from test_dynamics_policy_trainer import TRAINER, _venv_python

    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")
    prepared = _tracked(tmp_path)
    payload = prepared["path"].read_bytes()
    out = tmp_path / "tracked.cxpolicy"
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
    observed = container["header"]["observations"]
    assert observed[-2:] == ["ref_sin", "ref_cos"] and "elbow_angle_ref" not in observed
    evidence = dyn.verify_policy(container, prepared["bundle"],
                                 task_sha256=hashlib.sha256(payload).hexdigest())
    assert evidence["witness_error"] < dyn.POLICY_WITNESS_TOLERANCE
