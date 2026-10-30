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


def test_a_foot_body_is_kept_so_its_contact_is_as_soft_as_the_export():
    """ADR-951: fusing a foot into its shank changes the contact's ``invweight0`` softening; the cut keeps it."""

    options = {"timestep": 0.002, "iterations": 100, "ls_iterations": 50, "integrator": "implicitfast"}
    xml, kept = T.derive(EXPORT, **options)
    bodies = {b.get("name") for b in ET.fromstring(xml).iter("body")}
    assert {"c_foot_l", "c_foot_r"} <= bodies and "c_drum_l" not in bodies
    ctrl = T.controls(2, 0.1, 2.0, seconds=0.5)
    assert T.max_error(T.root_path(xml, ctrl), T.root_path(EXPORT, ctrl)) < 1e-6
    # The stand reads its feet from the named geoms when the export has no touch site.
    bare = EXPORT.replace('<touch site="obs/3/contact" name="obs/3"/>', "").replace(
        '<touch site="obs/4/contact" name="obs/4"/>', "")
    xml, _ = T.derive(bare, **options, feet=kept["feet"])
    assert T.stand(xml, 0.2, feet=kept["feet"])["on_feet_only"]
    assert not T.stand(xml, 0.2)["on_feet_only"]


def test_a_moved_inertia_or_a_framed_static_body_is_refused():
    xml, _ = T.derive(EXPORT, **T.DEFAULTS)
    root = ET.fromstring(xml)
    next(b for b in root.iter("body") if b.get("name") == "c_thigh_l").find("inertial").set("pos", "0 0.1 0.3")
    moved = ET.tostring(root, encoding="unicode")
    assert T.compare(T.compiled(EXPORT), T.compiled(moved))[0].startswith("mass matrix")
    with pytest.raises(ValueError, match="own frame"):
        T.derive(EXPORT.replace('<body name="c_panel">', '<body name="c_panel" pos="0 0 0.1">'), **T.DEFAULTS)


def test_the_bench_times_the_setting_the_cut_writes():
    """``cadex_train_bench`` overrides a model's options to each ``LADDER`` setting exactly as ``cut`` writes it."""

    import cadex_train_bench as B

    for setting in T.LADDER:
        xml, _ = T.derive(EXPORT, **setting)
        written = mujoco.MjModel.from_xml_string(xml).opt
        overridden = mujoco.MjModel.from_xml_string(EXPORT)
        B.apply_options(overridden, **setting)
        for name in ("timestep", "iterations", "ls_iterations", "integrator", "disableflags"):
            assert getattr(overridden.opt, name) == getattr(written, name), (setting, name)
        assert B.tier(xml) == "training" and B.tier(EXPORT) is None


def test_the_comparison_finds_the_legs_and_the_cut_unchanged(tmp_path):
    """``cadex_cad_vs_concept`` finds each leg from its touch site and reads a cut as its export."""

    import cadex_cad_vs_concept as C

    xml, _ = T.derive(EXPORT, **T.DEFAULTS)
    (tmp_path / "export.xml").write_text(EXPORT)
    (tmp_path / "cut.xml").write_text(xml)
    export, cut = C.measure(tmp_path / "export.xml"), C.measure(tmp_path / "cut.xml")
    assert {k: v["foot_site"] for k, v in export["legs"].items()} == {"c_thigh_l": "obs/3/contact", "c_thigh_r": "obs/4/contact"}
    assert list(export["joints"]) == ["j_hip_l", "j_hip_r"]
    rows = C.compare(export, cut)
    assert len(rows) == 5 + 2 * 5 + 2 * 5 and not any(r["flag"] for r in rows)
    assert max(abs(r["diff"]) for r in rows) < 1e-9
