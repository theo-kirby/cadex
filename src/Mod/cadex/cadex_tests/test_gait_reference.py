# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The procedural gait reference (ADR-702): footfall, scaling, IK and refusal.

Three claims, each against something the generator does not compute itself:
the contact schedule's touch-downs and duty factors are read back from the
0/1 series and compared with the gait table; the stride's joint angles are
pushed through MuJoCo's own forward kinematics and must land each foot on
its target; and a stride the legs cannot reach is refused with the leg, the
miss and the stops named, not clamped.
"""

from __future__ import annotations

import ast
import math
from pathlib import Path

import pytest

import CadexGait as gait

mujoco = pytest.importorskip("mujoco")
np = pytest.importorskip("numpy")

MODULE_DIR = Path(__file__).resolve().parent.parent

LEGS = {"LF": "foot_lf", "RF": "foot_rf", "LH": "foot_lh", "RH": "foot_rh"}


def _leg(name: str, x: float, y: float) -> str:
    return f"""
      <body name="yoke_{name}" pos="{x} {y} 0">
        <joint name="haa_{name}" type="hinge" axis="1 0 0" range="-20 20"/>
        <geom type="sphere" size="0.02" mass="0.3" contype="0" conaffinity="0"/>
        <body name="thigh_{name}">
          <joint name="hip_{name}" type="hinge" axis="0 1 0" range="-60 60"/>
          <geom type="capsule" fromto="0 0 0 0 0 -0.18" size="0.015" mass="0.5" contype="0" conaffinity="0"/>
          <body name="shin_{name}" pos="0 0 -0.18">
            <joint name="knee_{name}" type="hinge" axis="0 1 0" range="-130 0"/>
            <geom type="capsule" fromto="0 0 0 0 0 -0.18" size="0.012" mass="0.3" contype="0" conaffinity="0"/>
            <body name="foot_{name}" pos="0 0 -0.18">
              <geom name="pad_{name}" type="sphere" size="0.02" mass="0.05"/>
            </body>
          </body>
        </body>
      </body>"""


QUADRUPED = f"""
<mujoco model="gait-quadruped">
  <compiler angle="degree"/>
  <worldbody>
    <geom name="floor" type="plane" size="5 5 0.1"/>
    <body name="torso" pos="0 0 0.4">
      <freejoint name="root"/>
      <geom type="box" size="0.2 0.08 0.05" mass="6"/>
      {_leg("lf", 0.18, 0.1)}{_leg("rf", 0.18, -0.1)}
      <body name="pelvis" pos="-0.05 0 0">
        <joint name="spine" type="hinge" axis="0 1 0" range="-15 15"/>
        <geom type="box" size="0.06 0.07 0.04" mass="2" contype="0" conaffinity="0"/>
        {_leg("lh", -0.13, 0.1)}{_leg("rh", -0.13, -0.1)}
      </body>
    </body>
  </worldbody>
</mujoco>
"""


@pytest.fixture(scope="module")
def robot():
    model = mujoco.MjModel.from_xml_string(QUADRUPED)
    data = mujoco.MjData(model)
    home = model.qpos0.copy()
    for side in ("lf", "rf", "lh", "rh"):
        home[model.jnt_qposadr[model.joint(f"hip_{side}").id]] = math.radians(35)
        home[model.jnt_qposadr[model.joint(f"knee_{side}").id]] = math.radians(-70)
    data.qpos[:] = home
    mujoco.mj_kinematics(model, data)
    lowest = min(data.geom_xpos[model.geom(f"pad_{s}").id][2] for s in ("lf", "rf", "lh", "rh"))
    home[2] -= lowest - 0.02
    return model, home


def _clip(robot, name="trot", speed=0.8, **kw):
    model, home = robot
    return gait.generate(model, LEGS, name, speed, home_qpos=home, mujoco=mujoco, **kw)


@pytest.mark.parametrize("name", sorted(gait.GAITS))
def test_the_contact_schedule_is_the_gaits_footfall(name: str) -> None:
    table = gait.GAITS[name]
    samples = 400
    schedule = gait.contact_schedule(table["offsets"], table["duty"], samples)
    for foot in gait.FEET:
        series = schedule[foot]
        # duty factor: the share of the stride the foot is down
        assert sum(series) / samples == pytest.approx(table["duty"], abs=1.0 / samples)
        # touch-down: the one up->down edge, read off the cyclic series
        downs = [k for k in range(samples) if series[k] and not series[k - 1]]
        assert len(downs) == 1, (foot, downs)
        assert downs[0] / samples == pytest.approx(table["offsets"][foot] % 1.0, abs=1.0 / samples)


def test_the_named_gaits_have_their_defining_pairs() -> None:
    off = {name: g["offsets"] for name, g in gait.GAITS.items()}
    assert off["trot"]["LH"] == off["trot"]["RF"] and off["trot"]["RH"] == off["trot"]["LF"]
    assert off["pace"]["LH"] == off["pace"]["LF"] and off["pace"]["RH"] == off["pace"]["RF"]
    assert off["bound"]["LH"] == off["bound"]["RH"] and off["bound"]["LF"] == off["bound"]["RF"]
    assert off["half_bound"]["LH"] == off["half_bound"]["RH"] != off["half_bound"]["LF"]
    # a walk is four-beat with every foot a quarter apart; it is the only one down >half the time
    assert sorted(off["walk"].values()) == [0.0, 0.25, 0.5, 0.75]
    assert [n for n, g in gait.GAITS.items() if g["duty"] > 0.5] == ["walk"]


def test_stride_scales_by_dynamic_similarity() -> None:
    s = gait.stride(1.0, 0.4)
    froude = 1.0 / (gait.GRAVITY * 0.4)
    assert s["froude"] == pytest.approx(froude)
    assert s["stride_length_m"] == pytest.approx(2.3 * 0.4 * froude ** 0.3)
    assert s["stride_frequency_hz"] == pytest.approx(1.0 / s["stride_length_m"])
    # twice the hip height at the same Froude number: twice the stride, 1/sqrt(2) the frequency
    big = gait.stride(math.sqrt(2.0), 0.8)
    assert big["froude"] == pytest.approx(froude)
    assert big["stride_length_m"] == pytest.approx(2.0 * s["stride_length_m"])
    assert big["stride_frequency_hz"] == pytest.approx(s["stride_frequency_hz"] / math.sqrt(2.0))
    with pytest.raises(gait.GaitError) as refused:
        gait.stride(0.0, 0.4)
    assert refused.value.reason == "bad_speed"


def test_leg_chains_separate_the_spine_from_the_legs(robot) -> None:
    model, _home = robot
    found = gait.leg_chains(model, LEGS, mujoco=mujoco)
    names = {foot: [model.joint(j).name for j in js] for foot, js in found["chains"].items()}
    assert names["LF"] == ["haa_lf", "hip_lf", "knee_lf"]
    assert names["RH"] == ["haa_rh", "hip_rh", "knee_rh"]
    assert [model.joint(j).name for j in found["body_joints"]] == ["spine"]


def test_a_trot_round_trips_through_forward_kinematics(robot) -> None:
    model, home = robot
    clip = _clip(robot, spine_joint="spine", spine_amplitude_deg=5.0)
    assert clip["schema"] == gait.SCHEMA
    params = clip["parameters"]
    assert params["stride_length_source"] == "alexander_1976"
    assert clip["samples"] == round(params["period_s"] / clip["sample_dt_s"])
    data = mujoco.MjData(model)
    adr = {foot: model.body(LEGS[foot]).id for foot in gait.FEET}
    worst = 0.0
    for k, q in enumerate(clip["qpos"]):
        data.qpos[:] = q
        mujoco.mj_kinematics(model, data)
        for foot in gait.FEET:
            pad = data.geom_xpos[model.geom("pad_" + foot.lower()).id]
            worst = max(worst, float(np.linalg.norm(pad - clip["foot_positions_m"][foot][k])))
    assert worst < gait.TOLERANCE_M
    # every angle inside its joint's limits
    for row in clip["joint_angles_rad"]:
        for value, limit in zip(row, clip["joint_limits_rad"]):
            if limit is not None:
                assert limit[0] - 1e-9 <= value <= limit[1] + 1e-9
    # a foot that is down does not move in the world; a foot that is up clears the ground
    for foot in gait.FEET:
        path = np.array(clip["foot_positions_m"][foot])
        down = np.array(clip["contact"][foot], dtype=bool)
        ground = path[down][:, 2].min()
        assert np.allclose(path[down][:, 2], ground, atol=1e-9)
        runs = np.split(np.arange(len(down)), np.where(np.diff(down.astype(int)) != 0)[0] + 1)
        for run in runs:
            if down[run[0]] and run[0] > 0 and run[-1] < len(down) - 1:
                assert np.ptp(path[run][:, 0]) < 1e-9
        assert path[~down][:, 2].max() == pytest.approx(ground + params["swing_height_m"], rel=0.05)
    # a trot: diagonal feet share a schedule, lateral pairs are opposite
    assert clip["contact"]["LF"] == clip["contact"]["RH"]
    assert clip["contact"]["RF"] == clip["contact"]["LH"]
    assert params["duty_factor"] == gait.GAITS["trot"]["duty"]


def test_the_stride_is_periodic(robot) -> None:
    clip = _clip(robot)
    q = np.array(clip["joint_angles_rad"])
    # wrapping from the last sample to the first is one more step of the same motion
    steps = np.abs(np.diff(q, axis=0)).max(axis=0)
    wrap = np.abs(q[0] - q[-1])
    assert np.all(wrap <= 1.5 * steps + 1e-6)
    # and the body has travelled one stride less one sample
    params = clip["parameters"]
    travel = clip["body"]["x_m"][-1] - clip["body"]["x_m"][0]
    assert travel == pytest.approx(params["stride_length_m"] - params["speed_m_s"] * clip["sample_dt_s"])


def test_an_unreachable_stride_is_refused_with_the_reason(robot) -> None:
    with pytest.raises(gait.GaitUnreachable) as refused:
        _clip(robot, stride_length_m=2.0)
    error = refused.value
    assert error.reason == "unreachable"
    assert error.detail["leg"] in gait.FEET
    assert error.detail["miss_mm"] > gait.TOLERANCE_M * 1000
    assert error.detail["stride_length_m"] == 2.0
    assert "cannot reach" in str(error) and error.detail["leg"] in str(error)
    assert error.as_dict()["reason"] == "unreachable"


def test_requests_that_cannot_be_honoured_are_refused(robot) -> None:
    model, home = robot
    with pytest.raises(gait.GaitError) as unknown:
        _clip(robot, name="amble-ish")
    assert unknown.value.reason == "unknown_gait"
    with pytest.raises(gait.GaitError) as offsets:
        _clip(robot, name={"offsets": {"LF": 0.0, "RF": 0.5}, "duty": 0.5})
    assert offsets.value.reason == "bad_offsets"
    with pytest.raises(gait.GaitError) as duty:
        _clip(robot, name={"offsets": gait.GAITS["trot"]["offsets"], "duty": 1.0})
    assert duty.value.reason == "bad_duty"
    with pytest.raises(gait.GaitError) as spine:
        _clip(robot, spine_amplitude_deg=5.0)
    assert spine.value.reason == "no_spine_joint"
    with pytest.raises(gait.GaitError) as not_shared:
        _clip(robot, spine_joint="knee_lf")
    assert not_shared.value.reason == "bad_spine_joint"


def test_explicit_parameters_drive_the_same_generator(robot) -> None:
    custom = {"offsets": {"LH": 0.0, "LF": 0.1, "RH": 0.5, "RF": 0.6}, "duty": 0.55}
    clip = _clip(robot, name=custom, speed=0.5, stride_length_m=0.3)
    assert clip["gait"] == "custom"
    assert clip["parameters"]["stride_length_source"] == "given"
    assert clip["parameters"]["period_s"] == pytest.approx(0.6)
    downs = {f: [k for k, c in enumerate(s) if c and not s[k - 1]][0] / clip["samples"]
             for f, s in clip["contact"].items()}
    for foot, offset in custom["offsets"].items():
        assert downs[foot] == pytest.approx(offset, abs=1.0 / clip["samples"])


def test_the_module_loads_no_numerics_and_no_mujoco_at_import() -> None:
    tree = ast.parse((MODULE_DIR / "CadexGait.py").read_text(encoding="utf-8"))
    roots = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            roots.add((node.module or "").split(".")[0])
    assert roots <= {"__future__", "math", "typing"}
    assert "    CadexGait.py\n" in (MODULE_DIR / "CMakeLists.txt").read_text(encoding="utf-8")
