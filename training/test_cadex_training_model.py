# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-841: a training model cut from an export keeps its dynamics and touches the floor only with feet and trunk.

Needs ``mujoco`` (the training venv); no jax, no GPU. The export is a toy
written the way Cadex writes one: world-frame bodies, a joint-free panel and
knee drum, a sensor-named IMU body, a touch site per foot.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

mujoco = pytest.importorskip("mujoco")

import cadex_training_model as T  # noqa: E402


def _leg(s: str, y: float) -> str:
    return f"""
      <body name="c_thigh_{s}">
        <inertial pos="0 {y} 0.25" mass="0.5" diaginertia="0.004 0.004 0.001"/>
        <joint name="j_hip_{s}" pos="0 {y} 0.4" axis="0 1 0" range="-1 1" damping="0.5"/>
        <geom name="c_thigh_{s}/collision0" size="0.02 0.1" pos="0 {y} 0.25" type="capsule" contype="8" conaffinity="11"/>
        <body name="c_drum_{s}">
          <inertial pos="0 {y} 0.15" quat="0.9 0.1 0.3 0.2" mass="0.2" diaginertia="0.001 0.002 0.003"/>
          <geom name="c_drum_{s}/collision0" size="0.04" pos="0 {y} 0.15" contype="8" conaffinity="11"/>
        </body>
        <body name="c_foot_{s}">
          <inertial pos="0 {y} 0.03" mass="0.1" diaginertia="1e-5 1e-5 1e-5"/>
          <geom name="c_foot_{s}/collision0" size="0.03" pos="0 {y} 0.03" contype="2" conaffinity="3"/>
          <site name="obs/{y > 0 and 3 or 4}/contact" pos="0 {y} 0.03" size="0.03"/>
        </body>
      </body>"""


EXPORT = f"""<mujoco model="toy">
  <option integrator="implicitfast"><flag island="disable"/></option>
  <worldbody>
    <geom name="environment/floor" size="0 0 0.1" type="plane"/>
    <body name="c_trunk">
      <inertial pos="0 0 0.42" mass="3" diaginertia="0.02 0.04 0.05"/>
      <freejoint name="c_trunk/free"/>
      <geom name="c_trunk/collision0" size="0.15 0.12 0.03" pos="0 0 0.42" type="box" contype="4" conaffinity="11"/>
      <geom name="c_trunk/visual0" size="0.15 0.12 0.03" pos="0 0 0.42" type="box" contype="0" conaffinity="0"/>
      <body name="c_panel">
        <inertial pos="0.05 0 0.46" mass="0.2" diaginertia="0.001 0.001 0.001"/>
        <geom name="c_panel/collision0" size="0.05 0.05 0.01" pos="0.05 0 0.46" type="box" contype="4" conaffinity="11"/>
      </body>
      <body name="c_imu"><inertial pos="0 0 0.42" mass="0.01" diaginertia="1e-6 1e-6 1e-6"/></body>
      {_leg("l", 0.1)}{_leg("r", -0.1)}
    </body>
  </worldbody>
  <contact><exclude body1="c_trunk" body2="c_thigh_l"/></contact>
  <actuator>
    <general name="j_hip_l/position" joint="j_hip_l" biastype="affine" gainprm="50" biasprm="0 -50 -1"/>
    <general name="j_hip_r/position" joint="j_hip_r" biastype="affine" gainprm="50" biasprm="0 -50 -1"/>
  </actuator>
  <sensor>
    <framequat objtype="xbody" objname="c_imu" name="obs/0"/>
    <jointpos joint="j_hip_l" name="obs/1"/>
    <jointpos joint="j_hip_r" name="obs/2"/>
    <touch site="obs/3/contact" name="obs/3"/>
    <touch site="obs/4/contact" name="obs/4"/>
  </sensor>
</mujoco>
"""


def test_the_cut_keeps_the_dynamics_and_only_floor_pairs():
    xml, kept = T.derive(EXPORT, **T.DEFAULTS)
    assert sorted(kept["feet"]) == ["c_foot_l/collision0", "c_foot_r/collision0"]
    # The trunk's own geom and the panel fused into it; never a leg's.
    assert sorted(kept["fall_geoms"]) == ["c_panel/collision0", "c_trunk/collision0"]
    root = ET.fromstring(xml)
    assert root.find("contact") is None
    assert not {b.get("name") for b in root.iter("body")} & {"c_panel", "c_drum_l", "c_drum_r"}
    assert [t.get("data") for t in root.iter("text") if t.get("name") == "cadex:tier"] == ["training"]
    engine, train = T.compiled(EXPORT), T.compiled(xml)
    assert T.compare(engine, train) == []
    assert sorted(train["colliding"]) == sorted(kept["feet"] + kept["fall_geoms"])
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    d.qpos[2] = -0.5  # sink it whole: every floor geom touches, nothing else does
    mujoco.mj_forward(m, d)
    floor = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, T.FLOOR)
    dims = {m.geom(c.geom2 if c.geom1 == floor else c.geom1).name: int(c.dim) for c in d.contact[:d.ncon]}
    assert all(floor in (c.geom1, c.geom2) for c in d.contact[:d.ncon])
    assert set(dims) == set(kept["feet"] + kept["fall_geoms"])
    assert {dims[g] for g in kept["fall_geoms"]} == {1} and {dims[g] for g in kept["feet"]} == {3}


def test_a_moved_inertia_or_a_framed_static_body_is_refused():
    xml, _ = T.derive(EXPORT, **T.DEFAULTS)
    root = ET.fromstring(xml)
    next(b for b in root.iter("body") if b.get("name") == "c_thigh_l").find("inertial").set("pos", "0 0.1 0.3")
    moved = ET.tostring(root, encoding="unicode")
    assert T.compare(T.compiled(EXPORT), T.compiled(moved))[0].startswith("mass matrix")
    with pytest.raises(ValueError, match="own frame"):
        T.derive(EXPORT.replace('<body name="c_panel">', '<body name="c_panel" pos="0 0 0.1">'), **T.DEFAULTS)
