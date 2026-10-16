# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""A task can read the ground round a body: a height scan (ADR-715).

A ``height_scan`` observation on a component is its height in mm above the
ground at 15 points, 5 along its heading by 3 across it, 100 mm apart. The
ground is the declared course (ADR-714), read from the heightfield's own
elevation, or the plane at z = 0. It is no sensor: the bundle states it in a
``scans`` section, last in every vector, and the engine, the trainer and the
stock-MuJoCo reference runner each compute it from ``xpos``, ``xmat`` and
``hfield_data``. It is privileged (orun7 O5): the critic reads it, the
policy never does.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import subprocess

import pytest

import CadexDynamics as dyn
from test_dynamics_goal_model import _stock
from test_dynamics_policy_trainer import TRAINER, _trainer_module, _venv_python
from test_dynamics_terrain import COURSE, _free_block, _ground_z_mm
from test_dynamics_terrain_boxes import BOX_COURSE

mujoco = pytest.importorskip("mujoco")

SCAN = {"kind": "height_scan", "component": "block", "name": "scan", "role": "privileged"}
HOLD = {"kind": "position", "joint": "hinge", "motion_type": "angular", "name": "q"}
MOTOR = {"joint": "hinge", "motion_type": "angular", "kind": "motor",
         "control_nmm": "0", "torque_limit_nmm": 800.0}
TASK = {
    "actions": [{"joint": "hinge", "motion_type": "angular", "actuator_kind": "motor"}],
    "reward": [{"label": "clear", "expression": "scan_4 - abs(q) / 100", "weight": 1.0}],
    "termination": [],
    "episode_seconds": 0.4,
    "control_hz": 50,
    "randomisation": [],
    "label": "scan",
}


def scanned(observations=(HOLD, SCAN), *, terrain=COURSE, task=TASK,
            root: Path | None = None):
    """The block on the course, its height scanned: model, bundle and files."""

    components, joints, _ = _free_block()
    built = dyn.build_model(components, joints, actuators=[dict(MOTOR)], terrain=terrain)
    records = dyn.observation_records(
        [dict(entry) for entry in observations],
        built["tree"], built["joint_records"], built["actuators"])
    exported = dyn.export_mjcf(built, observations=records)
    reloaded = dyn.load_model(exported["xml"])
    bundle = dyn.task_records(built, reloaded, dict(task), observations=records)
    bundle["model"] = {
        "path": "outputs/model-model.xml", "output": "model",
        "bytes": len(exported["xml"]),
        "sha256": hashlib.sha256(exported["xml"]).hexdigest(),
        "mujoco_version": str(bundle["mujoco_version"]),
    }
    result = {"built": built, "model": reloaded, "bundle": bundle, "xml": exported["xml"]}
    if root is not None:
        (root / "outputs").mkdir(parents=True, exist_ok=True)
        (root / "outputs" / "model-model.xml").write_bytes(exported["xml"])
        path = root / "outputs" / "job-task.json"
        path.write_bytes(json.dumps(bundle, indent=2, sort_keys=True).encode("utf-8"))
        result["path"] = path
    return result


def _posed(model, x_mm: float, y_mm: float, z_mm: float, yaw_deg: float, pitch_deg: float = 0.0):
    """The block's free joint set to a pose, forward-computed."""

    data = mujoco.MjData(model)
    yaw, pitch = math.radians(yaw_deg) / 2.0, math.radians(pitch_deg) / 2.0
    # Yaw about z, then pitch about the turned y: qz * qy.
    qz = (math.cos(yaw), 0.0, 0.0, math.sin(yaw))
    qy = (math.cos(pitch), 0.0, math.sin(pitch), 0.0)
    quat = (qz[0] * qy[0], -qz[3] * qy[2], qz[0] * qy[2], qz[3] * qy[0])
    data.qpos[:3] = [x_mm / 1000.0, y_mm / 1000.0, z_mm / 1000.0]
    data.qpos[3:7] = quat
    mujoco.mj_forward(model, data)
    return data


# -- the bundle -------------------------------------------------------------

def test_a_scan_is_a_row_of_its_own_and_carries_no_sensor() -> None:
    prepared = scanned()
    bundle, compiled = prepared["bundle"], prepared["model"]
    plain = scanned(observations=(HOLD,), task={
        **TASK, "reward": [{"label": "still", "expression": "-abs(q)", "weight": 1.0}]})

    (row,) = bundle["scans"]
    assert row["channels"] == [f"scan_{index}" for index in range(15)]
    assert row["offsets_mm"] == [list(pair) for pair in dyn.HEIGHT_SCAN_OFFSETS_MM]
    assert row["offsets_mm"][4] == [0.0, 0.0]
    assert row["unit"] == "mm" and row["role"] == "privileged" and row["scale"] == 1000.0
    assert row["body_id"] == mujoco.mj_name2id(compiled, mujoco.mjtObj.mjOBJ_BODY, "block")
    assert compiled.nsensor == plain["model"].nsensor
    assert not any(record["kind"] == "height_scan" for record in bundle["observations"])
    assert dyn._task_channels(bundle)[-15:] == row["channels"]
    assert not set(dyn.policy_channels(bundle)) & set(row["channels"])
    assert "scans" not in plain["bundle"]
    assert "scans" in dyn.task_semantic_view(bundle)


def test_a_scan_for_the_policy_is_refused() -> None:
    with pytest.raises(dyn.DynamicsError) as raised:
        scanned(observations=(HOLD, {**SCAN, "role": "policy"}))
    assert raised.value.reason == "height_scan_not_privileged"


def test_a_scan_names_channels_that_clash_like_any() -> None:
    with pytest.raises(dyn.DynamicsError) as raised:
        scanned(observations=({**HOLD, "name": "scan_3"}, SCAN))
    assert raised.value.reason == "duplicate_observation_channel"


def test_a_scan_of_a_component_not_in_the_model_is_refused() -> None:
    with pytest.raises(dyn.DynamicsError) as raised:
        scanned(observations=(HOLD, {**SCAN, "component": "nowhere"}))
    assert raised.value.reason == "observation_component_missing"


# -- the reading ------------------------------------------------------------

def test_on_vertices_the_scan_reads_the_declared_course_exactly() -> None:
    """Placed on a vertex and square to the grid, every point is a vertex,
    so the reading is the declared features' height to the elevation's
    precision -- the step, the slope and the bump each under some point."""

    prepared = scanned()
    compiled, bundle = prepared["model"], prepared["bundle"]
    features = prepared["built"]["environment"]["terrain"]["features"]
    span = bundle["terrain"]["highest_mm"] - bundle["terrain"]["lowest_mm"]
    for x, y, yaw in [(300.0, 0.0, 0.0), (900.0, 100.0, 0.0), (200.0, 200.0, 90.0),
                      (500.0, -100.0, 180.0)]:
        data = _posed(compiled, x, y, 250.0, yaw)
        values = dyn.height_scan_values(bundle, data.xpos, data.xmat, compiled.hfield_data)
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        for (ahead, left), name in zip(dyn.HEIGHT_SCAN_OFFSETS_MM, bundle["scans"][0]["channels"]):
            px, py = x + c * ahead - s * left, y + s * ahead + c * left
            assert values[name] == pytest.approx(
                250.0 - dyn.terrain_height_mm(features, px, py), abs=1e-5 * span), (x, y, yaw, name)
    # The course is under the points: some read the step, some the bump.
    data = _posed(compiled, 300.0, 100.0, 250.0, 0.0)
    values = dyn.height_scan_values(bundle, data.xpos, data.xmat, compiled.hfield_data)
    assert values["scan_14"] == pytest.approx(250.0 - 80.0, abs=0.01)   # 600 ahead: past the step
    assert values["scan_2"] == pytest.approx(250.0 - 40.0, abs=0.01)    # (200, 200): the bump's top


def test_between_vertices_the_scan_reads_the_ground_mujoco_collides_with() -> None:
    """Turned 30 degrees and pitched, off every vertex: each point agrees
    with a ray cast down onto the heightfield, within a millimetre (MuJoCo
    splits a cell into two triangles; the scan reads it bilinearly)."""

    prepared = scanned()
    compiled, bundle = prepared["model"], prepared["bundle"]
    data = _posed(compiled, 437.0, -53.0, 300.0, 30.0, pitch_deg=12.0)
    values = dyn.height_scan_values(bundle, data.xpos, data.xmat, compiled.hfield_data)
    block = bundle["scans"][0]["body_id"]
    x, y, z = (float(v) * 1000.0 for v in data.xpos[block])
    for (ahead, left), name in zip(dyn.HEIGHT_SCAN_OFFSETS_MM, bundle["scans"][0]["channels"]):
        c, s = math.cos(math.radians(30.0)), math.sin(math.radians(30.0))
        px, py = x + c * ahead - s * left, y + s * ahead + c * left
        assert values[name] == pytest.approx(z - _ground_z_mm(compiled, px, py), abs=1.0), name


def test_off_the_course_a_point_reads_its_edge_and_on_flat_ground_the_plane() -> None:
    prepared = scanned()
    compiled, bundle = prepared["model"], prepared["bundle"]
    data = _posed(compiled, 1580.0, 0.0, 250.0, 0.0)
    values = dyn.height_scan_values(bundle, data.xpos, data.xmat, compiled.hfield_data)
    # 1680 and 1880 are past the course's end at 1600: they read its edge.
    assert values["scan_10"] == pytest.approx(values["scan_13"], abs=1e-9)

    flat = scanned(terrain=None)
    assert "terrain" not in flat["bundle"]
    data = _posed(flat["model"], 120.0, -40.0, 210.0, 45.0)
    values = dyn.height_scan_values(flat["bundle"], data.xpos, data.xmat, None)
    assert all(value == pytest.approx(210.0) for value in values.values())


def test_an_episode_scores_its_reward_on_the_scan() -> None:
    prepared = scanned()
    episode = dyn.evaluate_episode(prepared["model"], prepared["bundle"],
                                   actions=lambda step, obs: [math.sin(step)])
    for row in episode["steps"]:
        obs = row["observation"]
        (term,) = row["reward_terms"]
        assert term["value"] == pytest.approx(obs["scan_4"] - abs(obs["q"]) / 100.0)
    # The block stands at the origin, its centre 10 mm up on flat ground.
    assert episode["steps"][-1]["observation"]["scan_4"] == pytest.approx(10.0, abs=2.0)


@pytest.mark.parametrize("seed", [None, 5])
def test_a_stock_mujoco_reads_the_scan_the_engine_read(tmp_path: Path, seed) -> None:
    prepared = scanned(root=tmp_path)
    there = _stock(prepared["path"], seed)
    here = dyn.evaluate_episode(prepared["model"], prepared["bundle"], seed=seed)
    assert there["cadex_importable"] is False
    assert float(there["total_reward"]) == pytest.approx(here["total_reward"], abs=1e-9)
    for mine, yours in zip(here["steps"], there["steps"], strict=True):
        for name in prepared["bundle"]["scans"][0]["channels"]:
            assert float(yours["observation"][name]) == pytest.approx(
                mine["observation"][name], abs=1e-9)


def test_on_a_box_course_the_scan_reads_the_ray_and_the_runner_agrees(tmp_path: Path) -> None:
    """ADR-716: on placed boxes the scan reads the highest box top, which is
    where MuJoCo's own ray meets the boxes, and a stock MuJoCo reads it too."""

    prepared = scanned(terrain=BOX_COURSE, root=tmp_path)
    compiled, bundle = prepared["model"], prepared["bundle"]
    data = _posed(compiled, 1050.0, -120.0, 400.0, 20.0, pitch_deg=8.0)
    values = dyn.height_scan_values(bundle, data.xpos, data.xmat, None)
    block = mujoco.mj_name2id(compiled, mujoco.mjtObj.mjOBJ_BODY, "block")
    x, y, z = (float(v) * 1000.0 for v in data.xpos[block])
    heading = math.radians(20.0)
    for (ahead, left), name in zip(bundle["scans"][0]["offsets_mm"],
                                   bundle["scans"][0]["channels"], strict=True):
        px = x + math.cos(heading) * ahead - math.sin(heading) * left
        py = y + math.sin(heading) * ahead + math.cos(heading) * left
        assert values[name] == pytest.approx(z - _ground_z_mm(compiled, px, py), abs=1e-3), name
    there = _stock(prepared["path"], 3)
    here = dyn.evaluate_episode(compiled, bundle, seed=3)
    for mine, yours in zip(here["steps"], there["steps"], strict=True):
        for name in dyn.scan_channels(bundle):
            assert float(yours["observation"][name]) == pytest.approx(
                mine["observation"][name], abs=1e-9)


# -- the trainer ------------------------------------------------------------

def test_the_trainer_computes_the_engines_scan_on_a_box_course() -> None:
    numpy = pytest.importorskip("numpy")
    module = _trainer_module()
    prepared = scanned(terrain=BOX_COURSE)
    compiled, bundle = prepared["model"], prepared["bundle"]
    poses = [_posed(compiled, 1050.0, -120.0, 400.0, 20.0, pitch_deg=8.0),
             _posed(compiled, 1700.0, 380.0, 300.0, 170.0)]
    for data in poses:
        engine = dyn.height_scan_values(bundle, data.xpos, data.xmat, None)
        trained = module.height_scan_vector(numpy, bundle, numpy.asarray(data.xpos),
                                            numpy.asarray(data.xmat), None)
        assert trained.tolist() == pytest.approx(
            [engine[name] for name in dyn.scan_channels(bundle)], abs=1e-9)
    batch = module.height_scan_vector(
        numpy, bundle, numpy.stack([numpy.asarray(d.xpos) for d in poses]),
        numpy.stack([numpy.asarray(d.xmat) for d in poses]), None)
    assert batch.shape == (2, 15)


def test_the_trainer_computes_the_engines_scan() -> None:
    numpy = pytest.importorskip("numpy")
    module = _trainer_module()
    prepared = scanned()
    compiled, bundle = prepared["model"], prepared["bundle"]

    assert module.channels(bundle) == dyn._task_channels(bundle)
    assert module.actor_channels(bundle) == dyn.policy_channels(bundle)
    assert module.scan_channels(bundle) == dyn.scan_channels(bundle)
    assert len(module.sensor_variance_floor(bundle)) == len(module.channels(bundle))
    poses = [_posed(compiled, 437.0, -53.0, 300.0, 30.0, pitch_deg=12.0),
             _posed(compiled, 1580.0, 250.0, 260.0, -100.0)]
    elevation = numpy.asarray(compiled.hfield_data)
    for data in poses:
        engine = dyn.height_scan_values(bundle, data.xpos, data.xmat, compiled.hfield_data)
        expected = [engine[name] for name in dyn.scan_channels(bundle)]
        flat = module.height_scan_vector(numpy, bundle, numpy.asarray(data.xpos),
                                         numpy.asarray(data.xmat), elevation)
        square = module.height_scan_vector(numpy, bundle, numpy.asarray(data.xpos),
                                           numpy.asarray(data.xmat).reshape(-1, 3, 3), elevation)
        assert flat.tolist() == pytest.approx(expected, abs=1e-9)
        assert square.tolist() == pytest.approx(expected, abs=1e-9)
    batch = module.height_scan_vector(
        numpy, bundle, numpy.stack([numpy.asarray(d.xpos) for d in poses]),
        numpy.stack([numpy.asarray(d.xmat).reshape(-1, 3, 3) for d in poses]), elevation)
    assert batch.shape == (2, 15)
    source = inspect.getsource(module.build_environment)
    assert source.count("height_scan_vector(") == 2


def test_mjx_scans_the_course_the_engine_scans() -> None:
    """The trainer reads MJX's ``xpos`` and ``xmat`` and the model's
    ``hfield_data`` in ``jnp``; on the file the trainer loads, posed off
    every vertex, it reads what the engine reads from MuJoCo's."""

    mjx = pytest.importorskip("mujoco.mjx")
    jax = pytest.importorskip("jax")
    jnp = pytest.importorskip("jax.numpy")
    module = _trainer_module()
    prepared = scanned()
    compiled, bundle = prepared["model"], prepared["bundle"]
    for pose in [(437.0, -53.0, 300.0, 30.0, 12.0), (1580.0, 250.0, 260.0, -100.0, 0.0)]:
        data = _posed(compiled, *pose)
        engine = dyn.height_scan_values(bundle, data.xpos, data.xmat, compiled.hfield_data)
        there = mjx.forward(mjx.put_model(compiled), mjx.put_data(compiled, data))
        trained = module.height_scan_vector(
            jnp, bundle, there.xpos, there.xmat,
            jnp.asarray(compiled.hfield_data, dtype=jnp.float32))
        assert jax.device_get(trained).tolist() == pytest.approx(
            [engine[name] for name in dyn.scan_channels(bundle)], abs=0.05)


def test_the_trainer_trains_with_the_critic_reading_the_scan(tmp_path) -> None:
    """End to end: the scan in the critic's inputs and not the actor's, and
    the policy verified by the engine against the same bundle, on a box
    course (ADR-716): MJX steps this rig on placed boxes, where on ADR-714's
    heightfield it went non-finite. The course is drawn at random and
    re-drawn per episode (ADR-717), and the header says so."""

    from test_dynamics_terrain_random import RANDOM_COURSE

    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")
    prepared = scanned(terrain=RANDOM_COURSE, root=tmp_path, task={
        **TASK, "reward": [{"label": "clear", "expression": "scan_4 / 1000 - abs(q) / 1000",
                            "weight": 1.0}]})
    out = tmp_path / "scanned.cxpolicy"
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment["CUDA_VISIBLE_DEVICES"] = ""
    result = subprocess.run(
        [python, "-P", str(TRAINER), str(prepared["path"]),
         "--out", str(out), "--seed", "0", "--iterations", "3", "--envs", "8",
         "--unroll", "10", "--quiet"],
        capture_output=True, text=True, env=environment, check=False,
    )
    assert result.returncode == 0, result.stderr[-4000:]
    container = dyn.decode_policy(out.read_bytes())
    assert not set(container["header"]["observations"]) & set(dyn.scan_channels(prepared["bundle"]))
    assert container["header"]["training"]["terrain"] == {
        "mode": "per_episode", "algorithm": _trainer_module().TERRAIN_POOL_ALGORITHM,
        "bundle_algorithm": dyn.TERRAIN_RANDOM_ALGORITHM, "courses": 6}
    evidence = dyn.verify_policy(
        container, prepared["bundle"],
        task_sha256=hashlib.sha256(prepared["path"].read_bytes()).hexdigest())
    assert evidence["witness_error"] < dyn.POLICY_WITNESS_TOLERANCE


# -- the surface ------------------------------------------------------------

def test_the_surface_offers_a_height_scan_on_a_component() -> None:
    from test_dynamics_task_api import _api, _scene

    api = _api()
    scene = _scene(api)
    channel = api.observation(scene["components"][0], "height_scan", name="scan",
                              role="privileged")
    assert channel.properties["kind"] == "height_scan"
    with pytest.raises(ValueError):
        api.observation(scene["joints"][0], "height_scan", name="scan")


def test_describe_api_teaches_the_height_scan() -> None:
    from CadexScriptedRuntime import _capability_api_listing

    (observation,) = [entry for entry in _capability_api_listing()["assembly"]["exports"]
                      if entry["name"] == "observation"]
    assert "``height_scan``" in observation["description"]
    assert "ADR-715" in observation["description"]
