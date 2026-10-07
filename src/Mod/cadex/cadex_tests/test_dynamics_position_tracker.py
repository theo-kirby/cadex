# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A position tracker reads a free body in its mount's frame (ADR-588).

A touch panel on a tilting plate reads a ball's x and y; a camera on a mast
reads a marker. Before this, the only grounded sensors were an IMU and a
joint encoder, so a design that needed the position of a free object faked
it with joints nobody would build. The decisions worth testing:

* **The channel is the body's true position in the mount's frame**, through
  a tilt and a turn of the mount -- computed by stock MuJoCo (a ``framepos``
  with a reference frame), not by Cadex.
* **Out of range reads as out of range**: zeros and ``_in_range`` 0, which a
  termination can name -- never a clamped edge or the last value seen.
* **The declaration is applied**: readings round to the resolution, the
  trainer's noise has the declared spread, and its arithmetic is the
  engine's (the trainer cannot import the engine, so a test pins the copy).
* **It is grounded**: a task whose policy reads it is not ungrounded, and a
  tracker slower than the control loop is refused.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx
from cadex_assembly_api import AssemblyDomainAPI
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS

mujoco = pytest.importorskip("mujoco")

TRAINER = Path(__file__).resolve().parents[4] / "training" / "cadex_train.py"

TRACKER = {
    "range_mm": [[-90.0, 90.0], [-70.0, 70.0], [-5.0, 40.0]],
    "resolution_mm": 0.5,
    "rate_hz": 100.0,
    "noise_mm": 0.4,
}


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _trainer():
    spec = importlib.util.spec_from_file_location("cadex_train_tracker", TRAINER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# The surface.
# ---------------------------------------------------------------------------


def _surface():
    api = _api()
    parts = [
        api.component({"document_uid": "doc", "object_name": f"solid{i}"}, grounded=i == 0)
        for i in range(3)
    ]
    return api, parts


def test_a_tracker_is_declared_like_a_datasheet_and_reads_another_body() -> None:
    api, (_base, plate, ball) = _surface()
    touch = api.sensor(plate, "position_tracker", name="touch", **TRACKER)
    read = api.observation(ball, "tracked_position", name="ball", sensor=touch)

    assert read.properties["grounded_kind"] == "position_tracker"
    assert read.properties["grounded_sensor"] == "touch"
    declared = read.properties["tracker"]
    assert [list(pair) for pair in declared["range_mm"]] == TRACKER["range_mm"]
    assert {key: declared[key] for key in ("resolution_mm", "rate_hz", "noise_mm")} == {
        key: TRACKER[key] for key in ("resolution_mm", "rate_hz", "noise_mm")}
    # The mount travels as the second argument, which is how the worker
    # names the frame.
    assert read.arguments == (ball, plate)


def test_a_tracker_without_its_declaration_or_on_itself_is_refused() -> None:
    api, (_base, plate, ball) = _surface()
    for missing in TRACKER:
        partial = {key: value for key, value in TRACKER.items() if key != missing}
        with pytest.raises(ValueError, match=missing):
            api.sensor(plate, "position_tracker", name="touch", **partial)
    with pytest.raises(ValueError, match="range_mm"):
        api.sensor(plate, "position_tracker", name="touch",
                   **{**TRACKER, "range_mm": [[5.0, -5.0], [0, 1], [0, 1]]})
    with pytest.raises(ValueError, match="applies to a position_tracker"):
        api.sensor(plate, "imu", name="imu", noise_mm=0.1)
    touch = api.sensor(plate, "position_tracker", name="touch", **TRACKER)
    with pytest.raises(ValueError, match="another body"):
        api.observation(plate, "tracked_position", name="self", sensor=touch)
    # A tracked position with no tracker is a world position nobody measures.
    with pytest.raises(ValueError, match="position_tracker"):
        api.observation(ball, "tracked_position", name="ball", role="privileged")
    imu = api.sensor(plate, "imu", name="imu")
    with pytest.raises(ValueError, match="measures"):
        api.observation(ball, "tracked_position", name="ball", sensor=imu)


# ---------------------------------------------------------------------------
# The model: a plate that turns about z and tilts about x, and a free ball.
# ---------------------------------------------------------------------------


def _rig(turn_rad: float = 0.0, tilt_rad: float = 0.0):
    components, joints, _placements = fx.build(
        [
            {"name": "base", "grounded": True, "size": (200.0, 200.0, 20.0)},
            {"name": "yoke", "size": (60.0, 60.0, 20.0)},
            {"name": "plate", "size": (180.0, 140.0, 6.0)},
            {"name": "ball", "size": (20.0, 20.0, 20.0),
             "world": dyn.matrix_multiply(
                 fx.frame((25.0, -10.0, 90.0)), dyn.IDENTITY_MATRIX)},
        ],
        [
            {"name": "turn", "kind": "revolute", "parent": "base", "child": "yoke",
             "parent_frame": fx.frame((0.0, 0.0, 30.0)),
             "child_frame": fx.frame((0.0, 0.0, 0.0)),
             "angle_limits_degrees": [-170.0, 170.0], "values": [turn_rad]},
            {"name": "tilt", "kind": "revolute", "parent": "yoke", "child": "plate",
             "parent_frame": fx.frame((0.0, 0.0, 40.0), (0.0, 1.0, 0.0), 90.0),
             "child_frame": fx.frame((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 90.0),
             "angle_limits_degrees": [-30.0, 30.0], "values": [tilt_rad]},
        ],
    )
    return dyn.build_model(
        components, joints,
        actuators=[{"joint": "tilt", "motion_type": "angular", "kind": "position",
                    "control_deg": "0", "stiffness_nmm_per_deg": 4000.0,
                    "damping_nmms_per_deg": 120.0}],
        joint_dynamics=[],
    )


def _entry(tracker=TRACKER, **extra):
    return {"kind": "tracked_position", "component": "ball", "name": "ball",
            "frame": "plate", "tracker": dict(tracker),
            "grounded_sensor": "touch", "grounded_kind": "position_tracker", **extra}


TASK = {
    "actions": [{"joint": "tilt", "motion_type": "angular", "actuator_kind": "position"}],
    "reward": [{"label": "centre", "expression": "-(ball_x**2 + ball_y**2)",
                "weight": 1.0e-4}],
    "termination": [{"label": "off_panel", "expression": "ball_in_range", "below": 0.5}],
    "episode_seconds": 1.0,
    "control_hz": 50,
    "randomisation": [],
    "label": "centre",
}


def _bundle(entries, task=TASK):
    built = _rig()
    observations = dyn.observation_records(
        entries, built["tree"], built["joint_records"], built["actuators"])
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    bundle = dyn.task_records(built, reloaded, dict(task), observations=observations)
    return reloaded, bundle


def _true_in_plate(model, data) -> list[float]:
    plate = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "plate")
    ball = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "ball")
    rotation = data.xmat[plate].reshape(3, 3)
    delta = data.xpos[ball] - data.xpos[plate]
    return [1000.0 * float(sum(rotation[row][axis] * delta[row] for row in range(3)))
            for axis in range(3)]


def _set_pose(model, data, *, turn_deg, tilt_deg, ball_world_m):
    for joint, value in (("turn", turn_deg), ("tilt", tilt_deg)):
        index = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint)
        data.qpos[model.jnt_qposadr[index]] = math.radians(value)
    free = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "ball/free")
    adr = model.jnt_qposadr[free]
    data.qpos[adr:adr + 3] = ball_world_m
    mujoco.mj_forward(model, data)


def test_the_channel_is_the_body_in_the_mount_frame_through_a_tilt_and_a_turn() -> None:
    reloaded, bundle = _bundle([_entry()])
    task = bundle
    row = task["observations"][0]
    assert row["channels"] == ["ball_x", "ball_y", "ball_z", "ball_in_range"]
    assert (row["dim"], row["frame"], row["tracker"]) == (3, "plate", TRACKER)
    data = mujoco.MjData(reloaded)
    poses = [(0.0, 0.0), (35.0, 0.0), (0.0, -20.0), (-120.0, 17.5), (160.0, 28.0)]
    checked = 0
    for turn, tilt in poses:
        _set_pose(reloaded, data, turn_deg=turn, tilt_deg=tilt,
                  ball_world_m=[0.03, -0.02, 0.09])
        truth = _true_in_plate(reloaded, data)
        reading = dyn.observation_values(task, data.sensordata)
        if all(lo <= value <= hi for value, (lo, hi) in zip(truth, TRACKER["range_mm"])):
            assert reading["ball_in_range"] == 1.0, (turn, tilt, truth)
            for axis, value in zip("xyz", truth):
                # Rounded to the resolution, so within half a step of the truth.
                assert abs(reading[f"ball_{axis}"] - value) <= 0.25 + 1e-9, (turn, tilt)
                assert reading[f"ball_{axis}"] / 0.5 == pytest.approx(
                    round(reading[f"ball_{axis}"] / 0.5))
            checked += 1
    assert checked == len(poses)
    # The turn and the tilt moved the reading: a world-frame channel would
    # have read the same ball the same way at every pose.
    readings = set()
    for turn, tilt in poses[:3]:
        _set_pose(reloaded, data, turn_deg=turn, tilt_deg=tilt,
                  ball_world_m=[0.03, -0.02, 0.09])
        values = dyn.observation_values(task, data.sensordata)
        readings.add((values["ball_x"], values["ball_y"], values["ball_z"]))
    assert len(readings) == 3


def test_out_of_range_reads_zeros_and_a_flag_and_terminates() -> None:
    reloaded, bundle = _bundle([_entry()])
    task = bundle
    data = mujoco.MjData(reloaded)
    # 250 mm off the plate's centre: past range_mm's x edge at 90.
    _set_pose(reloaded, data, turn_deg=0.0, tilt_deg=0.0, ball_world_m=[0.25, 0.0, 0.09])
    truth = _true_in_plate(reloaded, data)
    assert truth[0] > 90.0
    assert dyn.observation_values(task, data.sensordata) == {
        "ball_x": 0.0, "ball_y": 0.0, "ball_z": 0.0, "ball_in_range": 0.0}
    # And the termination the task names on the flag fires.
    rule = task["termination"][0]
    assert rule["expression"] == "ball_in_range" and rule["below"] == 0.5
    # Just inside reads the position, not an edge.
    _set_pose(reloaded, data, turn_deg=0.0, tilt_deg=0.0, ball_world_m=[0.085, 0.0, 0.09])
    inside = dyn.observation_values(task, data.sensordata)
    assert inside["ball_in_range"] == 1.0
    assert inside["ball_x"] == pytest.approx(_true_in_plate(reloaded, data)[0], abs=0.25)


def test_quantisation_follows_the_declared_resolution() -> None:
    coarse = {**TRACKER, "resolution_mm": 2.0}
    assert dyn.tracker_reading([3.1, -4.9, 10.0], coarse) == [4.0, -4.0, 10.0, 1.0]
    assert dyn.tracker_reading([3.1, -4.9, 10.0], TRACKER) == [3.0, -5.0, 10.0, 1.0]
    # Noise is added before the rounding, as a real converter sees it.
    assert dyn.tracker_reading([3.1, 0.0, 0.0], coarse, [1.0, 0.0, 0.0]) == [4.0, 0.0, 0.0, 1.0]
    # Range is judged on the true position, so noise cannot drop a reading.
    assert dyn.tracker_reading([89.9, 0.0, 0.0], TRACKER, [5.0, 0.0, 0.0])[3] == 1.0
    assert dyn.tracker_reading([90.1, 0.0, 0.0], TRACKER, [-5.0, 0.0, 0.0]) == [0.0] * 4


def test_the_trainers_copy_is_the_engines_and_its_noise_has_the_declared_spread() -> None:
    np = pytest.importorskip("numpy")
    trainer = _trainer()
    rng = np.random.default_rng(7)
    for _ in range(200):
        truth = rng.uniform(-110.0, 110.0, size=3)
        noise = rng.normal(0.0, 0.4, size=3)
        theirs = trainer.tracker_reading(np, truth, TRACKER, noise)
        ours = dyn.tracker_reading(list(truth), TRACKER, list(noise))
        assert list(theirs) == pytest.approx(ours, abs=1e-9)
    task = {"observations": [
        {"name": "angle", "dim": 1, "channels": ["angle"]},
        {"name": "ball", "dim": 3, "tracker": TRACKER,
         "channels": ["ball_x", "ball_y", "ball_z", "ball_in_range"]},
    ]}
    assert trainer.tracker_noise_std(task) == [0.4, 0.4, 0.4]
    # The spread a training draw gives: the trainer scales a unit normal by
    # this vector, so the readings' deviation is the declaration's.
    draws = rng.standard_normal((20000, 3)) * np.asarray(trainer.tracker_noise_std(task))
    fine = {**TRACKER, "resolution_mm": 0.01}
    readings = np.asarray([
        trainer.tracker_reading(np, np.asarray([10.0, 0.0, 5.0]), fine, draw)[:3]
        for draw in draws[:4000]
    ])
    assert readings.std(axis=0) == pytest.approx([0.4, 0.4, 0.4], rel=0.06)
    assert readings.mean(axis=0) == pytest.approx([10.0, 0.0, 5.0], abs=0.03)


def test_a_task_reading_it_is_grounded_and_a_slow_tracker_is_refused() -> None:
    _reloaded, bundle = _bundle([_entry()])
    task = bundle
    assert dyn.ungrounded_policy_channels(task) == []
    assert dyn.policy_channels(task) == ["ball_x", "ball_y", "ball_z", "ball_in_range"]
    with pytest.raises(dyn.DynamicsError) as refused:
        _bundle([_entry({**TRACKER, "rate_hz": 30.0})])
    assert refused.value.reason == "tracker_slower_than_control"
    with pytest.raises(dyn.DynamicsError) as on_itself:
        _bundle([_entry(frame="ball")])
    assert on_itself.value.reason == "observation_tracker_frame"


# ---------------------------------------------------------------------------
# The normaliser (ADR-589): a tracked channel never reaches the policy at
# thousands of standard deviations.
# ---------------------------------------------------------------------------


def test_the_normaliser_floor_is_the_declarations_and_zero_elsewhere() -> None:
    trainer = _trainer()
    task = {
        "observations": [
            {"name": "angle", "dim": 1, "channels": ["angle"]},
            {"name": "ball", "dim": 3, "tracker": TRACKER,
             "channels": ["ball_x", "ball_y", "ball_z", "ball_in_range"]},
            {"name": "cam", "dim": 3, "tracker": {**TRACKER, "noise_mm": 0.0},
             "channels": ["cam_x", "cam_y", "cam_z", "cam_in_range"]},
        ],
        "goal": [{"name": "target", "channels": ["target_x"]}],
    }
    floor = trainer.tracker_variance_floor(task)
    assert len(floor) == len(trainer.channels(task))
    # The larger of resolution (0.5) and noise (0.4), squared; then the
    # resolution alone where the declaration has no noise; a flag's floor is
    # a fair flag's variance; nothing a tracker does not report is floored.
    assert floor == [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0]
    assert trainer.tracker_variance_floor({"observations": [
        {"name": "angle", "dim": 1, "channels": ["angle"]}]}) == [0.0]


def test_a_trained_policy_never_holds_a_tracked_channel_below_its_floor(tmp_path) -> None:
    """Through the real trainer. The range is the whole world, so the flag
    reads 1 on every step: without the floor its stored spread collapses to
    the normaliser's 1e-4 epsilon, and the first lost touch would reach the
    policy at ten thousand standard deviations. The measured case behind it
    was a ball's height above a panel, 51 deviations from noise alone."""

    import hashlib
    import json
    import os
    import subprocess

    from test_dynamics_policy_trainer import _venv_python

    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")
    everywhere = {**TRACKER, "range_mm": [[-1.0e5, 1.0e5]] * 3, "noise_mm": 0.0}
    built = _rig()
    observations = dyn.observation_records(
        [_entry(everywhere)], built["tree"], built["joint_records"], built["actuators"])
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    task = {**TASK, "termination": []}
    bundle = dyn.task_records(built, reloaded, task, observations=observations)
    bundle["model"] = {"path": "outputs/job-model.xml",
                       "sha256": hashlib.sha256(exported["xml"]).hexdigest(),
                       "bytes": len(exported["xml"]), "output": "job_model",
                       "mujoco_version": str(bundle["mujoco_version"])}
    payload = json.dumps(bundle, indent=2, sort_keys=True).encode("utf-8")
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "job-model.xml").write_bytes(exported["xml"])
    (tmp_path / "outputs" / "job-task.json").write_bytes(payload)
    out = tmp_path / "p.cxpolicy"
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [python, "-P", str(TRAINER), str(tmp_path / "outputs" / "job-task.json"),
         "--out", str(out), "--seed", "0", "--iterations", "3", "--envs", "8",
         "--unroll", "10", "--quiet"],
        capture_output=True, text=True, env=environment, check=False)
    assert result.returncode == 0, result.stderr[-4000:]
    container = dyn.decode_policy(out.read_bytes())
    header = container["header"]
    std = dict(zip(header["observations"], header["normaliser"]["std"]))
    assert std["ball_in_range"] >= 0.5
    for axis in "xyz":
        assert std[f"ball_{axis}"] >= 0.5 - 1e-6
    dyn.verify_policy(container, bundle, task_sha256=hashlib.sha256(payload).hexdigest())
