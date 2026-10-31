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
    # An identity frame is the world frame: such a body fuses (leon VI's tail links write pos="0 0 0").
    xml, _ = T.derive(EXPORT.replace('<body name="c_panel">', '<body name="c_panel" pos="0 0 0" quat="1 0 0 0">'),
                      **T.DEFAULTS)
    assert "c_panel" not in {b.get("name") for b in ET.fromstring(xml).iter("body")}


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


TAIL = """
      <body name="c_tail_1">
        <inertial pos="-0.2 0 0.42" mass="0.1" diaginertia="1e-4 1e-4 1e-5"/>
        <joint name="j_tail_pitch" pos="-0.15 0 0.42" axis="0 1 0" range="-0.3 0.5" damping="0.1"/>
        <body name="c_tail_2">
          <inertial pos="-0.3 0 0.41" mass="0.05" diaginertia="5e-5 5e-5 5e-6"/>
          <joint name="j_tail2_pitch" pos="-0.25 0 0.42" axis="0 1 0" range="-0.1 0.2"/>
          <body name="c_tail_3">
            <inertial pos="-0.4 0 0.40" mass="0.04" diaginertia="4e-5 4e-5 4e-6"/>
            <joint name="j_tail3_pitch" pos="-0.35 0 0.41" axis="0 1 0" range="-0.1 0.2"/>
            <geom name="c_tail_3/collision0" size="0.01 0.04" pos="-0.4 0 0.40" type="capsule" contype="4" conaffinity="11"/>
          </body>
        </body>
      </body>"""
COUPLED = """
  <equality>
    <joint name="coupling/cable_tail2" joint1="j_tail2_pitch" joint2="j_tail_pitch" polycoef="0 0.4 0 0 0"/>
    <joint name="coupling/cable_tail3" joint1="j_tail3_pitch" joint2="j_tail2_pitch" polycoef="0 1 0 0 0"/>
  </equality>
  <actuator>"""
TAILED = (EXPORT.replace('<body name="c_imu">', TAIL + '\n      <body name="c_imu">', 1)
          .replace("\n  <actuator>", COUPLED, 1)
          .replace("</actuator>", '  <general name="j_tail_pitch/position" joint="j_tail_pitch" biastype="affine" '
                   'gainprm="90" biasprm="0 -90 -1"/>\n  </actuator>'))


def test_a_held_cable_coupled_chain_is_welded_at_its_build_pose():
    """ADR-959: ``--weld`` takes the chain's hinges and their cables out; the rest of the dynamics is the export's."""

    xml, kept = T.derive(TAILED, **T.DEFAULTS, weld=["j_tail[23]_*"])
    welded = kept["welded"]
    assert welded["joints"] == ["j_tail2_pitch", "j_tail3_pitch"]
    assert welded["equalities"] == ["coupling/cable_tail2", "coupling/cable_tail3"]
    root = ET.fromstring(xml)
    assert root.find("equality") is None
    bodies = {b.get("name") for b in root.iter("body")}
    assert "c_tail_1" in bodies and not bodies & {"c_tail_2", "c_tail_3"}  # rigid now, fused into the root link
    engine, train = T.compiled(TAILED), T.compiled(xml)
    assert (train["nv"], train["neq"], train["nu"]) == (engine["nv"] - 2, engine["neq"] - 2, engine["nu"])
    assert T.compare(engine, train, welded) == []
    assert T.compare(engine, train)[0].startswith("nq")  # read as an unwelded cut, it is refused
    # The root drive still moves the whole tail, now one body, with the export's inertia about its hinge.
    m = mujoco.MjModel.from_xml_string(xml)
    assert "j_tail_pitch" in [m.joint(i).name for i in range(m.njnt)]
    # A keyframe drops the welded coordinates and keeps the others.
    keyed = TAILED.replace("</mujoco>", '  <keyframe><key name="home" qpos="0 0 0.02 1 0 0 0 0.1 0 0 0.2 -0.2"/></keyframe>\n</mujoco>')
    xml, _ = T.derive(keyed, **T.DEFAULTS, weld=["j_tail2_pitch", "j_tail3_pitch"])
    assert next(ET.fromstring(xml).iter("key")).get("qpos").split() == "0 0 0.02 1 0 0 0 0.1 0.2 -0.2".split()


@pytest.mark.parametrize("weld, why", [
    (["j_tail_pitch"], "actuated"),
    (["j_hip_r"], "actuated"),
    (["j_nothing*"], "matches no joint"),
])
def test_a_driven_or_unnamed_joint_is_not_welded(weld, why):
    with pytest.raises(ValueError, match=why):
        T.derive(TAILED, **T.DEFAULTS, weld=weld)


def test_an_uncoupled_sensed_or_posed_joint_is_not_welded():
    free = TAILED.replace('<joint name="coupling/cable_tail3" joint1="j_tail3_pitch" joint2="j_tail2_pitch" polycoef="0 1 0 0 0"/>', "")
    with pytest.raises(ValueError, match="no joint equality"):
        T.derive(free, **T.DEFAULTS, weld=["j_tail3_pitch"])
    sensed = TAILED.replace("</sensor>", '  <jointpos joint="j_tail3_pitch" name="obs/9"/>\n  </sensor>')
    with pytest.raises(ValueError, match="sensor"):
        T.derive(sensed, **T.DEFAULTS, weld=["j_tail3_pitch"])
    posed = TAILED.replace("</mujoco>", '  <keyframe><key qpos="0 0 0.02 1 0 0 0 0.1 0.05 0 0 0"/></keyframe>\n</mujoco>')
    with pytest.raises(ValueError, match="build pose"):
        T.derive(posed, **T.DEFAULTS, weld=["j_tail[23]_pitch"])
