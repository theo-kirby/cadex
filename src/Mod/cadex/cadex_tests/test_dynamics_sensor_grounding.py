# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Onboard sensors ground what a policy may read (ADR-408).

hex2 (2026-09-25) trained a hexapod policy on joint angles its MG90S servos
cannot report and on a centre-of-mass velocity nothing on the robot measures.
The decisions worth testing rather than reading:

* **A policy channel names the sensor that measures it.** An IMU measures its
  own component's orientation and rotation rate; a joint encoder its own
  joint's position and rate. Anything else the policy would read is refused
  at the surface, where the script is.
* **A privileged channel is for the reward and the critic only**, and the
  policy never reads it: :func:`CadexDynamics.policy_channels` is what a
  policy header is checked against.
* **The refusal to train bites at training, not at the build**, and a task
  written before ADR-408 exports byte-identical, so every policy trained on
  one still verifies.
"""

from __future__ import annotations

import pytest

import CadexDynamics as dyn
from cadex_assembly_api import AssemblyDomainAPI, _PUBLISHABLE_TYPES
from cadex_domain_api import _DOMAIN_OPERATION_OUTPUT_TYPES
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from CadexScriptedDomainPublication import _NATIVE_TYPE_BY_OUTPUT


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _scene(api):
    components = [
        api.component({"document_uid": "doc", "object_name": f"solid{i}"}, grounded=i == 0)
        for i in range(3)
    ]
    joints = [
        api.joint("revolute", api.connector(components[i], "origin"),
                  api.connector(components[i + 1], "origin"))
        for i in range(2)
    ]
    return components, joints


def test_sensor_is_an_intermediate_like_an_observation() -> None:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    assert "sensor" in pack.api_exports
    assert "sensor" not in pack.output_types
    assert "sensor" not in _PUBLISHABLE_TYPES
    assert "sensor" not in _NATIVE_TYPE_BY_OUTPUT
    assert _DOMAIN_OPERATION_OUTPUT_TYPES["assembly"]["sensor"] == "sensor"


def test_a_grounded_channel_names_its_sensor_and_a_legacy_one_names_nothing() -> None:
    api = _api()
    components, joints = _scene(api)
    imu = api.sensor(components[1], "imu", name="imu")
    encoder = api.sensor(joints[0], "joint_encoder", name="knee")
    rot = api.observation(components[1], "component_orientation", name="rot", sensor=imu)
    gyro = api.observation(components[1], "component_angular_velocity", name="gyro", sensor=imu)
    angle = api.observation(joints[0], "position", name="angle", sensor=encoder)
    com = api.observation(components[1], "centre_of_mass", name="com", role="privileged")
    legacy = api.observation(joints[1], "position", name="other")

    assert (rot.properties["grounded_sensor"], rot.properties["grounded_kind"]) == ("imu", "imu")
    assert gyro.properties["grounded_sensor"] == "imu"
    assert angle.properties["grounded_kind"] == "joint_encoder"
    assert com.properties["role"] == "privileged" and "grounded_sensor" not in com.properties
    # The defaults add nothing, which is what keeps a pre-ADR-408 task's bytes.
    for key in ("role", "grounded_sensor", "grounded_kind"):
        assert key not in legacy.properties


def test_a_sensor_only_grounds_what_it_measures_on_what_it_is_mounted_on() -> None:
    api = _api()
    components, joints = _scene(api)
    imu = api.sensor(components[1], "imu", name="imu")
    encoder = api.sensor(joints[0], "joint_encoder", name="knee")
    with pytest.raises(ValueError, match="measures"):
        api.observation(components[1], "centre_of_mass_velocity", name="v", sensor=imu)
    with pytest.raises(ValueError, match="measures its own"):
        api.observation(components[2], "component_orientation", name="rot", sensor=imu)
    with pytest.raises(ValueError, match="measures its own"):
        api.observation(joints[1], "position", name="a", sensor=encoder)
    with pytest.raises(ValueError, match="measures"):
        api.observation(components[1], "component_orientation", name="rot", sensor=encoder)
    with pytest.raises(ValueError, match="api.sensor"):
        api.observation(joints[0], "position", name="a", sensor=joints[0])


def test_the_sensor_and_role_arguments_are_checked() -> None:
    api = _api()
    components, joints = _scene(api)
    with pytest.raises(ValueError, match="kind"):
        api.sensor(components[1], "lidar", name="x")
    with pytest.raises(ValueError, match="target"):
        api.sensor(joints[0], "imu", name="x")
    with pytest.raises(ValueError, match="target"):
        api.sensor(components[1], "joint_encoder", name="x")
    with pytest.raises(ValueError, match="name"):
        api.sensor(components[1], "imu", name="2fast")
    with pytest.raises(ValueError, match="role"):
        api.observation(joints[0], "position", name="a", role="secret")


def _task(*rows):
    return {"observations": [
        {"name": name, "channels": list(channels), **extra}
        for name, channels, extra in rows
    ]}


def test_the_policy_reads_everything_not_privileged_in_task_order() -> None:
    task = _task(
        ("rot", ["rot_qw", "rot_qx", "rot_qy", "rot_qz"],
         {"grounded_sensor": "imu", "grounded_kind": "imu"}),
        ("com", ["com_x", "com_y", "com_z"], {"role": "privileged"}),
        ("angle", ["angle"], {}),
    )
    assert dyn.policy_channels(task) == ["rot_qw", "rot_qx", "rot_qy", "rot_qz", "angle"]
    assert dyn.ungrounded_policy_channels(task) == ["angle"]
    legacy = _task(("angle", ["angle"], {}), ("com", ["com_x"], {}))
    assert dyn.policy_channels(legacy) == ["angle", "com_x"]
    assert dyn.ungrounded_policy_channels(legacy) == ["angle", "com_x"]
