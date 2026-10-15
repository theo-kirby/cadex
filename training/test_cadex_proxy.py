# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-710: the drive proxy loop edits an exported model and screens it.

Needs ``mujoco`` and ``numpy`` (the training venv); no jax, no GPU. The model
is a one-legged toy: a free base and a hinged leg under a position drive,
following a sine reference.
"""

from __future__ import annotations

import json
import math

import pytest

mujoco = pytest.importorskip("mujoco")
np = pytest.importorskip("numpy")

import cadex_proxy as P  # noqa: E402

LIBRARY = {
    # CadexCatalog.QDD_ACTUATORS' AK80-9 V3.0 and AK70-10, the fields the proxy reads.
    "ak80-9": {"model": "AK80-9", "gear_ratio": 9.0, "rated_torque_nm": 9.0, "peak_torque_nm": 22.0,
               "no_load_speed_rpm": 570.0, "rotor_inertia_gcm2": 1118.3238,
               "back_drive_torque_nm": 0.51, "mass_g": 490.0},
    "ak70-10": {"model": "AK70-10", "gear_ratio": 10.0, "rated_torque_nm": 8.3, "peak_torque_nm": 24.8,
                "no_load_speed_rpm": 480.0, "rotor_inertia_gcm2": 753.4788,
                "back_drive_torque_nm": 0.48, "mass_g": 621.0},
    "big": {"model": "big", "gear_ratio": 9.0, "rated_torque_nm": 18.0, "peak_torque_nm": 53.0,
            "no_load_speed_rpm": 320.0, "rotor_inertia_gcm2": 1002.0, "mass_g": 940.0},
    "weak": {"model": "weak", "gear_ratio": 6.0, "rated_torque_nm": 0.5, "peak_torque_nm": 1.0,
             "no_load_speed_rpm": 400.0, "rotor_inertia_gcm2": 100.0, "mass_g": 200.0},
}

XML = """
<mujoco>
  <option timestep="0.002"/>
  <worldbody>
    <geom name="floor" type="plane" size="2 2 0.1"/>
    <body name="base" pos="0 0 0.35">
      <freejoint name="base/free"/>
      <geom type="box" size="0.15 0.08 0.04" mass="3"/>
      <body name="housing" pos="0 0 0"><geom type="cylinder" size="0.04 0.02" mass="0.49"/></body>
      <body name="leg" pos="0 0 0">
        <joint name="j_leg" axis="0 1 0" range="-1 1" damping="0.368569" armature="0.00905842" frictionloss="0.51"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.02" mass="0.6"/>
        <body name="foot" pos="0 0 -0.3"><geom type="sphere" size="0.02" mass="0.3"/></body>
      </body>
    </body>
  </worldbody>
  <actuator>
    <general name="j_leg/position" joint="j_leg" forcelimited="true" forcerange="-22 22"
             biastype="affine" gainprm="60" biasprm="0 -60 -1"/>
  </actuator>
  <keyframe><key name="solved" qpos="0 0 0.35 1 0 0 0 0"/></keyframe>
</mujoco>
"""

SAMPLES = 25


def task(amplitude_deg: float = 30.0) -> dict:
    # A bundle's table holds the posed channels only; the clock pair is computed.
    table = [[amplitude_deg * math.sin(2 * math.pi * k / SAMPLES)] for k in range(SAMPLES)]
    return {
        "actions": [{"joint": "j_leg", "index": 0, "low": -45.0, "high": 45.0,
                     "scale": math.pi / 180.0, "rated_effort": 9000.0}],
        "episode": {"max_steps": 100, "solver_steps_per_action": 10, "control_interval_s": 0.02,
                    "reset_keyframe": "solved"},
        "reference": {"parameters": {"speed_m_s": 0.0}},
        "tracking": {"channels": ["ref_sin", "ref_cos", "q_leg_ref"], "samples": SAMPLES, "table": table},
    }


def fresh():
    return mujoco.MjModel.from_xml_string(XML)


def body(model, name):
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)


def test_a_drive_reads_as_lib_qdd_exports_it():
    # The cat's exported scapula joint (AK80-9) carries exactly these.
    c = P.drive_constants(LIBRARY["ak80-9"])
    assert c["damping"] == pytest.approx(0.368569, rel=1e-5)
    assert c["armature"] == pytest.approx(0.00905842, rel=1e-5)
    assert (c["peak_nm"], c["rated_nm"], c["mass_kg"]) == (22.0, 9.0, 0.49)
    with pytest.raises(P.ProxyError, match="rated above its peak"):
        P.drive_constants(dict(LIBRARY["ak80-9"], rated_torque_nm=30.0))
    with pytest.raises(P.ProxyError, match="positive mass_g"):
        P.drive_constants({k: v for k, v in LIBRARY["ak80-9"].items() if k != "mass_g"})


def test_the_as_built_drive_is_identified_by_its_clamp_and_rating():
    assert P.identify_drive(LIBRARY, 22.0, 9.0) == "ak80-9"
    assert P.identify_drive(LIBRARY, 22.0, None) == "ak80-9"
    assert P.identify_drive(LIBRARY, 22.0, 8.3) is None
    assert P.identify_drive(dict(LIBRARY, twin=LIBRARY["ak80-9"]), 22.0, 9.0) is None


def test_a_swap_moves_the_clamp_the_line_the_rotor_and_the_mass():
    model = fresh()
    before = float(model.body_mass[body(model, "base")])
    rows = P.apply(mujoco, model, task(), {"drives": {"j_leg": "big"}}, LIBRARY)
    assert rows == [{"joint": "j_leg", "slot": 0, "drive": "big", "peak_nm": 53.0, "rated_nm": 18.0,
                     "no_load_rad_s": pytest.approx(320.0 * P.RPM)}]
    assert list(model.actuator_forcerange[0]) == [-53.0, 53.0]
    big = P.drive_constants(LIBRARY["big"])
    assert model.dof_damping[6] == pytest.approx(big["damping"])
    assert model.dof_armature[6] == pytest.approx(big["armature"])
    # No back-drive torque on the datasheet: the joint keeps its friction loss.
    assert model.dof_frictionloss[6] == pytest.approx(0.51)
    # The housing is the joint's parent body, here the base itself.
    assert model.body_mass[body(model, "base")] == pytest.approx(before + 0.94 - 0.49)


def test_a_swap_with_a_back_drive_rating_takes_it():
    model = fresh()
    P.apply(mujoco, model, task(), {"drives": {"j_leg": "ak70-10"}}, LIBRARY)
    assert model.dof_frictionloss[6] == pytest.approx(0.48)


def test_moving_mass_inboard_and_scaling_keep_the_books():
    model = fresh()
    total = float(model.body_mass.sum())
    P.apply(mujoco, model, task(), {"move_mass": [{"from": "foot", "to": "housing", "fraction": 1.0}]},
            LIBRARY)
    assert model.body_mass[body(model, "foot")] == 0.0
    assert model.body_mass[body(model, "housing")] == pytest.approx(0.79)
    assert float(model.body_mass.sum()) == pytest.approx(total)
    model = fresh()
    P.apply(mujoco, model, task(), {"mass_scale": 0.5}, LIBRARY)
    assert float(model.body_mass.sum()) == pytest.approx(total / 2)


@pytest.mark.parametrize("config, message", [
    ({"drives": {"j_nope": "big"}}, "not a joint this task actuates"),
    ({"drives": {"j_leg": "nope"}}, "not in the drive library"),
    ({"move_mass": [{"from": "foot", "to": "base", "kg": 0.1, "fraction": 0.1}]}, "one of kg or fraction"),
    ({"move_mass": [{"from": "foot", "to": "base", "kg": 1.0}]}, "would leave body"),
    ({"move_mass": [{"from": "ghost", "to": "base", "kg": 0.1}]}, "no body named"),
    ({"mass_scale": 0.0}, "mass_scale must be positive"),
    ({"drive": {}}, "unknown configuration keys"),
])
def test_a_configuration_is_refused_with_a_reason(config, message):
    with pytest.raises(P.ProxyError, match=message):
        P.apply(mujoco, fresh(), task(), config, LIBRARY)


def test_an_unknown_drive_cannot_be_swapped():
    library = {k: v for k, v in LIBRARY.items() if k != "ak80-9"}
    with pytest.raises(P.ProxyError, match="matches no library drive"):
        P.apply(mujoco, fresh(), task(), {"drives": {"j_leg": "big"}}, library)


def screened(config, support="full", amplitude=30.0):
    model = fresh()
    rows = P.apply(mujoco, model, task(amplitude), config, LIBRARY)
    return P.screen(mujoco, np, model, task(amplitude), rows, 7, support=support)


def test_a_held_replay_rates_each_drive_against_its_datasheet():
    run = screened({})
    assert run["completed"] and run["survived_s"] == pytest.approx(2.0)
    assert run["start_sample"] == __import__("random").Random(7).randrange(SAMPLES)
    (drive,) = run["drives"]
    assert drive["rms_over_rated"] == pytest.approx(drive["rms_nm"] / 9.0)
    assert drive["speed_over_no_load"] > 0.0
    # A drive too weak for the swing sits at its clamp; a strong one does not.
    weak = screened({"drives": {"j_leg": "weak"}}, amplitude=40.0)["drives"][0]
    strong = screened({"drives": {"j_leg": "big"}}, amplitude=40.0)["drives"][0]
    assert weak["peak_share"] > 0.5 and strong["peak_share"] == 0.0
    assert weak["peak_needed_over_peak"] == pytest.approx(1.0, abs=1e-6)


def test_swing_leaves_only_what_moving_the_leg_costs():
    still = screened({}, support="swing", amplitude=0.0)["drives"][0]
    swinging = screened({}, support="swing")["drives"][0]
    assert still["rms_nm"] < 0.05 < swinging["rms_nm"]
    # Moving the leg's far mass inboard makes the swing cheaper.
    inboard = screened({"move_mass": [{"from": "foot", "to": "housing", "fraction": 1.0}]},
                       support="swing")["drives"][0]
    assert inboard["rms_nm"] < swinging["rms_nm"]


def test_an_unsupported_base_falls_and_says_when():
    model = fresh()
    rows = P.apply(mujoco, model, task(), {}, LIBRARY)
    run = P.screen(mujoco, np, model, task(), rows, 7, gain=0.0)
    assert not run["completed"] and run["survived_s"] < 2.0


def test_a_task_without_a_reference_is_refused():
    t = task()
    del t["tracking"]
    with pytest.raises(P.ProxyError, match="no gait reference"):
        P.screen(mujoco, np, fresh(), t, [], 1)


def test_the_command_line_writes_the_table(tmp_path, capsys):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "toy-model.xml").write_text(XML)
    bundle = dict(task(), model={"path": "outputs/toy-model.xml"})
    (outputs / "toy-task.json").write_text(json.dumps(bundle))
    (tmp_path / "drives.json").write_text(json.dumps(dict(LIBRARY, _note="ignored")))
    (tmp_path / "configs.json").write_text(json.dumps([{"name": "as-built"},
                                                       {"name": "big", "drives": {"j_leg": "big"}}]))
    code = P.main([str(outputs / "toy-task.json"), "--drives", str(tmp_path / "drives.json"),
                   "--configs", str(tmp_path / "configs.json"), "--seeds", "1", "2",
                   "--support", "full", "swing", "--joints", "j_leg", "--out", str(tmp_path / "sweep")])
    assert code == 0
    rows = json.loads((tmp_path / "sweep.json").read_text())
    assert [(r["name"], r["support"]) for r in rows] == [
        ("as-built", "full"), ("as-built", "swing"), ("big", "full"), ("big", "swing")]
    table = (tmp_path / "sweep.md").read_text().splitlines()
    assert table[0].startswith("| config | support |") and len(table) == 6
    (tmp_path / "configs.json").write_text(json.dumps([{"drives": {"j_leg": "nope"}}]))
    assert P.main([str(outputs / "toy-task.json"), "--drives", str(tmp_path / "drives.json"),
                   "--configs", str(tmp_path / "configs.json"), "--out", str(tmp_path / "x")]) == 2
    assert "not in the drive library" in capsys.readouterr().err
