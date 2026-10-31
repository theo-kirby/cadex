# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-958: cadex_joystick.py makes the source bundle's actions its actions and holds the rest.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_cadex_joystick.py`` from the repo.
"""

from __future__ import annotations

import json

import pytest

import cadex_joystick as J

pytest.importorskip("mujoco")

#: A floating trunk on a floor with two legs and a tail, each joint a position
#: servo: the tail plays leon VI's held root drive.
ROBOT = """
<mujoco><option timestep="0.002"/><worldbody>
  <geom name="floor" type="plane" size="5 5 0.1"/>
  <body name="trunk" pos="0 0 0.3"><freejoint/>
    <geom type="box" size="0.15 0.05 0.03" mass="2"/>
    <body name="leg_f" pos="0.1 0 0"><joint name="j_f" type="hinge" axis="0 1 0" range="-60 60"/>
      <geom type="capsule" fromto="0 0 0 0 0 -0.2" size="0.01" mass="0.1" contype="0" conaffinity="0"/>
      <body name="paw_f" pos="0 0 -0.25"><geom type="sphere" size="0.02" mass="0.05"/></body></body>
    <body name="leg_h" pos="-0.1 0 0"><joint name="j_h" type="hinge" axis="0 1 0" range="-60 60"/>
      <geom type="capsule" fromto="0 0 0 0 0 -0.2" size="0.01" mass="0.1" contype="0" conaffinity="0"/>
      <body name="paw_h" pos="0 0 -0.25"><geom type="sphere" size="0.02" mass="0.05"/></body></body>
    <body name="tail" pos="-0.15 0 0"><joint name="j_tail" type="hinge" axis="0 1 0" range="-30 30"/>
      <geom type="capsule" fromto="0 0 0 -0.2 0 0" size="0.01" mass="0.05" contype="0" conaffinity="0"/></body>
  </body></worldbody>
<actuator>
  <position name="j_f/position" joint="j_f" kp="20"/>
  <position name="j_h/position" joint="j_h" kp="20"/>
  <position name="j_tail/position" joint="j_tail" kp="20"/>
</actuator>
<keyframe><key name="home" qpos="0 0 0.3 1 0 0 0 0 0 0" ctrl="CTRL"/></keyframe></mujoco>"""


def bundle(tmp_path, actuators, ctrl="0 0 0"):
    outputs = tmp_path / "src" / "outputs"
    outputs.mkdir(parents=True)
    (outputs / "robot.xml").write_text(ROBOT.replace("CTRL", ctrl), encoding="utf-8")
    task = {"label": "robot", "model": {"path": "outputs/robot.xml"},
            "episode": {"control_interval_s": 0.02, "reset_keyframe": "home"},
            "variation_algorithm": "test",
            "actions": [{"actuator": a} for a in actuators]}
    path = outputs / "task.json"
    path.write_text(json.dumps(task), encoding="utf-8")
    return path


def written(report):
    return json.loads(open(report["task"], encoding="utf-8").read())


def test_held_drive_stays_out_of_actions_and_observations(tmp_path):
    report = J.write(bundle(tmp_path, ["j_f/position", "j_h/position"]), tmp_path / "out",
                     (0.7, 0.4, 0.6), "goto", ["paw_f", "paw_h"])
    task = written(report)
    assert report["actions"] == 2 and report["held"] == ["j_tail/position"]
    assert [a["actuator"] for a in task["actions"]] == ["j_f/position", "j_h/position"]
    assert [a["index"] for a in task["actions"]] == [0, 1]
    assert [c["target"] for c in task["commands"]] == ["j_f", "j_h"]
    targets = {o["target"] for o in task["observations"]}
    assert "j_tail" not in targets and "j_tail/position" not in targets
    assert not any("j_tail" in r["expression"] for r in task["reward"])
    assert not any(r["subject"] == "j_tail" for r in task["randomisation"])


def test_bundle_without_actions_drives_every_actuator(tmp_path):
    report = J.write(bundle(tmp_path, []), tmp_path / "out", (0.7, 0.4, 0.6), "goto", ["paw_f", "paw_h"])
    assert report["actions"] == 3 and report["held"] == []
    assert [a["joint"] for a in written(report)["actions"]] == ["j_f", "j_h", "j_tail"]


def test_held_drive_with_a_keyframe_command_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="held drive 'j_tail/position'"):
        J.write(bundle(tmp_path, ["j_f/position", "j_h/position"], ctrl="0 0 0.2"), tmp_path / "out",
                (0.7, 0.4, 0.6), "goto", ["paw_f", "paw_h"])


def test_action_not_in_the_model_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="not actuators"):
        J.write(bundle(tmp_path, ["j_f/position", "j_nose/position"]), tmp_path / "out",
                (0.7, 0.4, 0.6), "goto", ["paw_f", "paw_h"])
