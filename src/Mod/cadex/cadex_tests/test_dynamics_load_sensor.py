# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A load sensor reads the effort an actuator applies (ADR-591).

A bus servo reports its load over the bus; a hobby PWM servo reports
nothing. Before this, an actuator's effort was a privileged channel only, so
a design whose precision hinged on servo sag could not give its policy the
reading the servo really makes. The decisions worth testing:

* **The channel is the applied effort**: under a held load it reads the
  torque gravity puts on the joint, and it **saturates at the stall line**,
  the actuator's own effort limit, while the arm sags.
* **The declaration is applied**: readings round to the resolution, the
  trainer's noise has the declared spread, and its arithmetic is the
  engine's.
* **It is grounded where real hardware is**: a bus servo's ``load_sensor``
  fills the catalog's figures, a PWM servo's is refused with the reason, a
  task reading it is not ungrounded, and a load sensor slower than the
  control loop is refused.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest

import CadexCatalog as catalog
import CadexDynamics as dyn
import dynamics_fixtures as fx
from cadex_assembly_api import AssemblyDomainAPI
from cadex_domain_api import create_domain_api
from cadex_library_api import LibraryError, create_library_api
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS

TRAINER = Path(__file__).resolve().parents[4] / "training" / "cadex_train.py"

LOAD = {"full_scale": 1000.0, "resolution": 2.0, "rate_hz": 100.0, "noise": 15.0}


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _lib(api: AssemblyDomainAPI):
    pack = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
    part = create_domain_api(pack.domain, pack.api_exports, pack.output_types)
    return create_library_api(part, api)


def _trainer():
    spec = importlib.util.spec_from_file_location("cadex_train_load", TRAINER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _joint(api):
    base = api.component({"document_uid": "doc", "object_name": "base"}, grounded=True)
    arm = api.component({"document_uid": "doc", "object_name": "arm"})
    return api.joint("revolute", api.connector(base), api.connector(arm))


# ---------------------------------------------------------------------------
# The surface.
# ---------------------------------------------------------------------------


def test_a_load_sensor_reads_its_own_actuator_to_a_declared_datasheet() -> None:
    api = _api()
    motor = api.actuator(_joint(api), kind="position", control_deg="0",
                         stiffness_nmm_per_deg=200.0, torque_limit_nmm=1000.0)
    load = api.sensor(motor, "load_sensor", name="load",
                      resolution_nmm=2.0, noise_nmm=15.0, rate_hz=100.0)
    read = api.observation(motor, "actuator_force", name="effort", sensor=load)
    assert read.properties["grounded_kind"] == "load_sensor"
    assert read.properties["grounded_sensor"] == "load"
    assert dict(read.properties["load"]) == LOAD


def test_a_load_sensor_without_its_declaration_or_a_stall_line_is_refused() -> None:
    api = _api()
    joint = _joint(api)
    motor = api.actuator(joint, kind="position", control_deg="0",
                         stiffness_nmm_per_deg=200.0, torque_limit_nmm=1000.0)
    sheet = {"resolution_nmm": 2.0, "noise_nmm": 15.0, "rate_hz": 100.0}
    for missing in sheet:
        partial = {key: value for key, value in sheet.items() if key != missing}
        with pytest.raises(ValueError, match=missing):
            api.sensor(motor, "load_sensor", name="load", **partial)
    # A turning joint's load is in N*mm; the sliding unit is a refusal.
    with pytest.raises(ValueError, match="resolution_n"):
        api.sensor(motor, "load_sensor", name="load", resolution_n=1.0,
                   noise_nmm=15.0, rate_hz=100.0)
    with pytest.raises(ValueError, match="applies to a position_tracker"):
        api.sensor(motor, "load_sensor", name="load", range_mm=[[0, 1]] * 3, **sheet)
    with pytest.raises(ValueError, match="applies to a load_sensor"):
        api.sensor(joint, "joint_encoder", name="enc", noise_nmm=1.0)
    # No effort limit, no stall line for the reading to saturate at.
    unlimited = api.actuator(joint, kind="position", control_deg="0",
                             stiffness_nmm_per_deg=200.0)
    with pytest.raises(ValueError, match="no effort limit"):
        api.sensor(unlimited, "load_sensor", name="load", **sheet)
    # It reads its own actuator, and only that actuator's effort.
    load = api.sensor(motor, "load_sensor", name="load", **sheet)
    with pytest.raises(ValueError, match="measures its own"):
        api.observation(unlimited, "actuator_force", name="other", sensor=load)
    with pytest.raises(ValueError, match="measures"):
        api.observation(joint, "position", name="angle", sensor=load)


def test_a_bus_servo_grounds_a_load_sensor_and_a_pwm_servo_is_refused() -> None:
    api = _api()
    lib = _lib(api)
    joint = _joint(api)
    bus = lib.servo("sts3215")
    motor = bus.actuator(joint, control_deg="0", voltage=7.4)
    stall = 19.5 * catalog.KG_CM_TO_NMM
    load = bus.load_sensor(motor, name="load")
    declared = dict(load.properties["load"])
    assert declared["full_scale"] == pytest.approx(stall)
    # The register's 0.1 % count, and the catalog's assumed 1 % noise.
    assert declared["resolution"] == pytest.approx(0.001 * stall)
    assert declared["noise"] == pytest.approx(0.01 * stall)
    assert declared["rate_hz"] == 100.0
    assert bus.load_sensor(motor, name="load", rate_hz=200.0).properties["load"]["rate_hz"] == 200.0
    # Only the actuator this servo's .actuator made.
    stranger = api.actuator(joint, kind="position", control_deg="0",
                            stiffness_nmm_per_deg=200.0, torque_limit_nmm=123.0)
    with pytest.raises(LibraryError, match="actuator this sts3215"):
        bus.load_sensor(stranger, name="load")
    # Every catalogued servo either reports load or is a PWM servo, and every
    # PWM one refuses with the reason.
    for sku, row in catalog.SERVOS.items():
        if row.get("load_feedback"):
            assert row["family"] == "bus", sku
            continue
        pwm = lib.servo(sku)
        with pytest.raises(LibraryError, match="PWM") as refused:
            pwm.load_sensor(pwm.actuator(joint, control_deg="0"), name="load")
        assert "sts3215" in str(refused.value)


# ---------------------------------------------------------------------------
# The model: an arm held against gravity by a position servo.
# ---------------------------------------------------------------------------

#: Where the arm is solved; the servo holds it at 0 degrees, because a raw
#: ``mj_step`` leaves ``ctrl`` at zero and the hinge is off-vertical there.
START_RAD = 0.7


def _entry(load=LOAD):
    return {"kind": "actuator_force", "joint": "hinge", "motion_type": "angular",
            "actuator_kind": "position", "name": "effort",
            "grounded_sensor": "load", "grounded_kind": "load_sensor", "load": dict(load)}


def _task(control_hz=50):
    return {
        "actions": [{"joint": "hinge", "motion_type": "angular", "actuator_kind": "position"}],
        "reward": [{"label": "hold", "expression": "-abs(effort)", "weight": 1.0e-3}],
        "termination": [],
        "episode_seconds": 1.0,
        "control_hz": control_hz,
        "randomisation": [],
        "label": "hold",
    }


def _held(torque_limit_nmm: float, load=LOAD, control_hz=50):
    mujoco = pytest.importorskip("mujoco")
    # fx.pendulum, with both endpoints declared so the action range derives.
    components, joints, _placements = fx.build(
        [{"name": "base", "grounded": True, "size": (200.0, 200.0, 20.0)},
         {"name": "arm", "size": (300.0, 40.0, 20.0)}],
        [{"name": "hinge", "kind": "revolute", "parent": "base", "child": "arm",
          "parent_frame": fx.frame((40.0, -15.0, 60.0), (1.0, 0.0, 0.0), 90.0),
          "child_frame": fx.frame((-120.0, 5.0, 0.0), (0.0, 1.0, 0.0), -35.0),
          "angle_limits_degrees": [-170.0, 170.0], "values": [START_RAD]}],
    )
    built = dyn.build_model(
        components, joints,
        actuators=[{"joint": "hinge", "motion_type": "angular", "kind": "position",
                    "control_deg": "0",
                    "stiffness_nmm_per_deg": 3000.0, "damping_nmms_per_deg": 300.0,
                    "torque_limit_nmm": torque_limit_nmm}],
    )
    observations = dyn.observation_records(
        [_entry({**load, "full_scale": torque_limit_nmm})], built["tree"],
        built["joint_records"], built["actuators"])
    exported = dyn.export_mjcf(built, observations=observations)
    model = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    task = dyn.task_records(built, model, _task(control_hz), observations=observations)
    return mujoco, model, task


def _settle(mujoco, model, seconds=3.0):
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    for _ in range(int(seconds / model.opt.timestep)):
        mujoco.mj_step(model, data)
    mujoco.mj_forward(model, data)
    hinge = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "hinge")
    return data, int(model.jnt_dofadr[hinge]), int(model.jnt_qposadr[hinge])


def test_the_channel_tracks_a_held_load_and_saturates_at_the_stall_line() -> None:
    mujoco, model, task = _held(20000.0)
    row = task["observations"][0]
    assert row["load"] == {**LOAD, "full_scale": 20000.0}
    data, dof, qadr = _settle(mujoco, model)
    # Held: the arm is at its setpoint, and the servo's effort is exactly
    # what gravity puts on the joint -- qfrc_bias, in N*m.
    gravity_nmm = 1000.0 * float(data.qfrc_bias[dof])
    assert abs(gravity_nmm) > 500.0, "the fixture must load the joint"
    reading = dyn.observation_values(task, data.sensordata)["effort"]
    assert reading == pytest.approx(gravity_nmm, abs=LOAD["resolution"] / 2 + 5.0)
    assert reading / LOAD["resolution"] == pytest.approx(round(reading / LOAD["resolution"]))
    held_at = float(data.qpos[qadr])

    # A servo whose stall is half that load cannot hold it: the arm sags off
    # its setpoint and the reading sits on the stall line, not past it.
    stall = round(abs(gravity_nmm) / 2.0)
    mujoco, weak_model, weak_task = _held(float(stall))
    weak, _dof, weak_qadr = _settle(mujoco, weak_model, seconds=1.0)
    sagged = dyn.observation_values(weak_task, weak.sensordata)["effort"]
    assert abs(sagged) == pytest.approx(stall, abs=LOAD["resolution"])
    assert math.copysign(1.0, sagged) == math.copysign(1.0, gravity_nmm)
    assert abs(float(weak.qpos[weak_qadr]) - held_at) > math.radians(5.0)


def test_quantisation_and_saturation_follow_the_declaration() -> None:
    assert dyn.load_reading(10.9, LOAD) == 10.0
    assert dyn.load_reading(-11.1, LOAD) == -12.0
    # Noise is added before the rounding and the stall line holds it.
    assert dyn.load_reading(10.0, LOAD, 3.2) == 14.0
    assert dyn.load_reading(990.0, LOAD, 40.0) == 1000.0
    assert dyn.load_reading(-5000.0, LOAD) == -1000.0


def test_the_trainers_copy_is_the_engines_and_its_noise_has_the_declared_spread() -> None:
    np = pytest.importorskip("numpy")
    trainer = _trainer()
    rng = np.random.default_rng(11)
    for _ in range(300):
        truth = float(rng.uniform(-1300.0, 1300.0))
        noise = float(rng.normal(0.0, 15.0))
        theirs = float(trainer.load_reading(np, np.float64(truth), LOAD, np.float64(noise)))
        assert theirs == pytest.approx(dyn.load_reading(truth, LOAD, noise), abs=1e-9)
    tracker = {"range_mm": [[-1.0, 1.0]] * 3, "resolution_mm": 0.5,
               "rate_hz": 100.0, "noise_mm": 0.4}
    task = {"observations": [
        {"name": "angle", "dim": 1, "channels": ["angle"]},
        {"name": "effort", "dim": 1, "load": LOAD, "channels": ["effort"]},
        {"name": "ball", "dim": 3, "tracker": tracker,
         "channels": ["ball_x", "ball_y", "ball_z", "ball_in_range"]},
    ]}
    # In observation order, which is the order the trainer's draw is sliced.
    assert trainer.sensor_noise_std(task) == [15.0, 0.4, 0.4, 0.4]
    assert trainer.sensor_variance_floor(task) == pytest.approx(
        [0.0, 225.0, 0.25, 0.25, 0.25, 0.25])
    fine = {**LOAD, "resolution": 0.01}
    draws = rng.standard_normal(4000) * trainer.sensor_noise_std(task)[0]
    readings = np.asarray([trainer.load_reading(np, np.float64(300.0), fine, draw)
                           for draw in draws])
    assert readings.std() == pytest.approx(15.0, rel=0.06)
    assert readings.mean() == pytest.approx(300.0, abs=1.0)


def test_a_task_reading_it_is_grounded_and_a_slow_load_sensor_is_refused() -> None:
    _mujoco, _model, task = _held(20000.0)
    assert dyn.ungrounded_policy_channels(task) == []
    assert dyn.policy_channels(task) == ["effort"]
    with pytest.raises(dyn.DynamicsError) as refused:
        _held(20000.0, control_hz=200)
    assert refused.value.reason == "load_sensor_slower_than_control"
