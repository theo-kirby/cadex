# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-845: a CAD task bundle re-laid by name reads, drives and draws the same things on another model.

Needs ``mujoco`` (the training venv); no jax, no GPU. The export is a toy
written the way Cadex writes one; the other model numbers its legs the other
way round, fused the battery into the trunk and carries its own sensors.
"""

from __future__ import annotations

import hashlib
import json

import pytest

mujoco = pytest.importorskip("mujoco")
np = pytest.importorskip("numpy")

import cadex_relay as R  # noqa: E402
from cadex_train import function_names, globals_for, load_bundle  # noqa: E402


def _leg(s: str, y: float) -> str:
    return f"""
      <body name="c_thigh_{s}">
        <inertial pos="0 {y} 0.25" mass="0.5" diaginertia="0.004 0.004 0.001"/>
        <joint name="j_hip_{s}" pos="0 {y} 0.4" axis="0 1 0" range="-1 1"/>
        <geom size="0.02 0.1" pos="0 {y} 0.25" type="capsule"/>
        <body name="c_foot_{s}">
          <inertial pos="0 {y} 0.05" mass="0.1" diaginertia="1e-5 1e-5 1e-5"/>
          <joint name="j_knee_{s}" pos="0 {y} 0.15" axis="0 1 0" range="-1 1"/>
          <geom size="0.03" pos="0 {y} 0.05"/>
          {f'<site name="obs/4/contact" pos="0 {y} 0.03" size="0.03"/>' if s == "l" else ""}
        </body>
      </body>"""


def _model(legs: str, battery: bool, sensors: str) -> str:
    extra = ('<body name="c_battery"><inertial pos="0.05 0 0.46" mass="0.4" '
             'diaginertia="0.001 0.001 0.001"/></body>') if battery else ""
    drives = "".join(f'<position name="j_{j}_{s}/position" joint="j_{j}_{s}" kp="20"/>'
                     for s in "lr" for j in ("hip", "knee"))
    return f"""<mujoco model="toy">
  <worldbody>
    <geom name="floor" size="0 0 0.1" type="plane"/>
    <body name="c_trunk">
      <inertial pos="0 0 0.42" mass="3" diaginertia="0.02 0.04 0.05"/>
      <freejoint name="c_trunk/free"/>
      <geom size="0.15 0.12 0.03" pos="0 0 0.42" type="box"/>
      {extra}{legs}
    </body>
  </worldbody>
  <actuator>{drives}</actuator>
  <sensor>{sensors}</sensor>
  <keyframe><key name="solved"/></keyframe>
</mujoco>"""


EXPORT = _model(_leg("l", 0.1) + _leg("r", -0.1), True,
                '<framequat objtype="xbody" objname="c_trunk" name="obs/0"/>'
                '<jointpos joint="j_knee_r" name="obs/1"/>'
                '<subtreecom body="c_battery" name="obs/2"/>'
                '<actuatorfrc actuator="j_hip_r/position" name="obs/3"/>'
                '<touch site="obs/4/contact" name="obs/4"/>')
# The cut's legs the other way round, the battery fused into the trunk, and
# its own instruments in another order.
CUT = _model(_leg("r", -0.1) + _leg("l", 0.1), False,
             '<jointpos joint="j_hip_l" name="obs/0"/>'
             '<touch site="obs/4/contact" name="obs/1"/>').replace(
    'mass="3"', 'mass="3.4"')


def _observation(name: str, sensor: str, adr: int, dim: int, channels: list[str]) -> dict:
    return {"name": name, "sensor": sensor, "adr": adr, "dim": dim, "scale": 1.0,
            "channels": channels}


def _bundle(tmp_path) -> tuple:
    export = mujoco.MjModel.from_xml_string(EXPORT)
    qpos = [list(map(float, export.qpos0 + np.arange(export.nq) * 0.01))]
    task = {
        "schema": "cadex-training-task-v1",
        "functions": function_names(globals_for(np)),
        "model": {"path": "outputs/model-model.xml", "sha256":
                  hashlib.sha256(EXPORT.encode()).hexdigest()},
        "observations": [
            _observation("rot", "obs/0", 0, 4, ["qw", "qx", "qy", "qz"]),
            _observation("knee_r", "obs/1", 4, 1, ["knee_r"]),
            _observation("pack", "obs/2", 5, 3, ["px", "py", "pz"]),
            _observation("tau", "obs/3", 8, 1, ["tau"]),
            _observation("cl", "obs/4", 9, 1, ["cl"])],
        "actions": [{"actuator": f"j_{j}_{s}/position", "index": i}
                    for i, (s, j) in enumerate((s, j) for s in "lr" for j in ("hip", "knee"))],
        "reward": [{"expression": "knee_r + cl", "label": "r", "weight": 1.0}],
        "termination": [],
        "randomisation": [
            {"label": "mass", "subject": "c_trunk", "low": 0.9, "high": 1.1,
             "fields": [{"field": "body_mass", "index": 1},
                        {"field": "body_inertia", "index": 4}]},
            {"label": "mass", "subject": "c_battery", "low": 0.9, "high": 1.1,
             "fields": [{"field": "body_mass", "index": 2}]},
            {"label": "knee", "subject": "j_knee_r", "low": 0.9, "high": 1.1,
             "fields": [{"field": "dof_damping", "index": 9}]}],
        "reset_variation": [{"label": "rv", "body": "c_trunk", "body_id": 1,
                             "qpos_adr": 0, "qvel_adr": 0}],
        "disturbance": [{"label": "kick", "body": "c_foot_r", "body_id": 6},
                        {"label": "pack", "body": "c_battery", "body_id": 2}],
        "tracking": {"reset_qpos": qpos},
    }
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "model-model.xml").write_text(EXPORT)
    (tmp_path / "outputs" / "walk-task.json").write_text(json.dumps(task))
    (tmp_path / "cut.xml").write_text(CUT)
    return export, task


def test_relay_maps_by_name_and_drops_what_the_model_lacks(tmp_path):
    export, task = _bundle(tmp_path)
    out = tmp_path / "relaid"
    assert R.main([str(tmp_path / "outputs" / "walk-task.json"), str(tmp_path / "cut.xml"),
                   "--out", str(out)]) == 0
    bundle = load_bundle(str(out / "outputs" / "walk-task.json"), globals_for(np))
    relaid, report = bundle["task"], json.loads((out / "relay.json").read_text())
    cut = mujoco.MjModel.from_xml_string(bundle["model_xml"].decode())

    def body(m, n):
        return mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, n)

    def joint(m, n):
        return mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)

    # The battery's subtree sensor goes with its observation; the rest keep the
    # export's channels, and each address reads the same joint on the cut.
    assert report["sensors_dropped"] == {"obs/2": ["body c_battery"]}
    assert report["observations_dropped"] == ["pack"]
    assert [o["name"] for o in relaid["observations"]] == ["rot", "knee_r", "tau", "cl"]
    data = mujoco.MjData(cut)
    data.qpos[:] = relaid["tracking"]["reset_qpos"][0]
    mujoco.mj_forward(cut, data)
    knee = relaid["observations"][1]
    assert data.sensordata[knee["adr"]] == pytest.approx(
        task["tracking"]["reset_qpos"][0][int(export.jnt_qposadr[joint(export, "j_knee_r")])])
    assert data.qpos[cut.jnt_qposadr[joint(cut, "j_knee_r")]] == pytest.approx(
        data.sensordata[knee["adr"]])
    # Drives, bodies and randomised rows by name; what the cut fused is dropped, said.
    assert [a["index"] for a in relaid["actions"]] == [
        mujoco.mj_name2id(cut, mujoco.mjtObj.mjOBJ_ACTUATOR, a["actuator"])
        for a in task["actions"]]
    assert relaid["disturbance"] == [{**task["disturbance"][0],
                                      "body_id": body(cut, "c_foot_r")}]
    assert report["entries_dropped"] == ["task.disturbance: pack on c_battery"]
    assert report["randomisation_dropped"] == ["task.randomisation: mass on c_battery"]
    trunk, knee_r = relaid["randomisation"]
    assert [f["index"] for f in trunk["fields"]] == [1, 4]
    assert knee_r["fields"][0]["index"] == int(cut.jnt_dofadr[joint(cut, "j_knee_r")])
    # A dropped channel a reward reads refuses rather than trains wrong.
    task["reward"][0]["expression"] = "pz"
    (tmp_path / "outputs" / "walk-task.json").write_text(json.dumps(task))
    assert R.main([str(tmp_path / "outputs" / "walk-task.json"), str(tmp_path / "cut.xml"),
                   "--out", str(tmp_path / "refused")]) == 2
