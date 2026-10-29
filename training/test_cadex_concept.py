# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-834: a concept spec is written as the engine writes a model, so tools read it by name.

Needs ``mujoco`` (the training venv); no jax, no GPU. The spec is
``examples/concept/leon-iv.json``.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

mujoco = pytest.importorskip("mujoco")

import cadex_concept as C  # noqa: E402

SPEC = json.loads((Path(__file__).resolve().parents[1] / "examples" / "concept" / "leon-iv.json")
                  .read_text(encoding="utf-8"))


def compiled(spec):
    xml, report = C.build(spec)
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return model, data, report


def test_layout_is_the_exports():
    model, _, report = compiled(SPEC)
    names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, i) for i in range(model.nu)]
    assert names == [f"{j}/position" for j in report["actuated"]]
    assert names[:3] == ["j_fhaa_l/position", "j_shoulder_l/position", "j_elbow_l/position"]
    assert names[-2:] == ["j_spine/position", "j_spine_yaw/position"]
    sensors = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_SENSOR, i) for i in range(model.nsensor)]
    assert sensors == [f"obs/{i}" for i in range(model.nsensor)]
    # Three per drive, the IMU's two, the root's two, two per foot.
    assert model.nsensor == 3 * model.nu + 2 + 2 + 2 * 4
    assert mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "solved") == 0


def test_feet_rest_on_the_floor_and_right_mirrors_left():
    model, data, _ = compiled(SPEC)
    gaps = []
    for foot in ("c_paw_fl", "c_paw_fr", "c_paw_hl", "c_paw_hr"):
        geom = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, f"{foot}/collision0")
        gaps.append(data.geom_xpos[geom][2] - model.geom_size[geom][0])
    assert min(gaps) == pytest.approx(0.0, abs=1e-6)
    left, right = (mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, n) for n in ("j_hip_l", "j_hip_r"))
    assert list(model.jnt_range[right]) == pytest.approx([-model.jnt_range[left][1], -model.jnt_range[left][0]])
    assert model.jnt_pos[right][1] == pytest.approx(-model.jnt_pos[left][1])


def test_a_set_moves_the_stance():
    _, _, base = compiled(SPEC)
    longer = C.apply_sets(SPEC, ["legs.1.joints.1.length=0.2"])
    _, _, moved = compiled(longer)
    hind = next(r for r in moved["legs"] if r["foot"] == "c_paw_hl")
    was = next(r for r in base["legs"] if r["foot"] == "c_paw_hl")
    assert hind["hip_height_m"] > was["hip_height_m"]
    assert SPEC["legs"][1]["joints"][1]["length"] == 0.1492


def test_a_datasheet_drive_is_the_proxys():
    xml, _ = C.build(SPEC)
    model = mujoco.MjModel.from_xml_string(xml)
    hip = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "j_hip_l")
    dof = model.jnt_dofadr[hip]
    assert model.dof_damping[dof] == pytest.approx(53.0 / (320.0 * 2 * math.pi / 60), rel=1e-5)
    assert model.dof_armature[dof] == pytest.approx(1002.0e-7 * 81, rel=1e-5)
    with pytest.raises(C.ConceptError):
        C.build(C.apply_sets(SPEC, ['drives.ak10-9.kp="x"']))


def test_a_view_is_a_mesh_per_body_and_a_trace_of_them(tmp_path):
    """ADR-835: what the trainer leaves beside progress.json is what the dashboard plays."""

    import cadex_train as T

    xml, _ = C.build(SPEC)
    model = mujoco.MjModel.from_xml_string(xml)
    poses = [model.key_qpos[0]] * 3
    trace = json.loads(T.write_view(tmp_path, xml.encode("utf-8"), poses, 0.02, source="test")
                       .read_text(encoding="utf-8"))
    meshes = {path.stem for path in tmp_path.glob("*.stl")}
    assert "c_chest_frame" in meshes and "c_paw_hl" in meshes
    assert [frame["nominal_time_s"] for frame in trace["frames"]] == [0.0, 0.02, 0.04]
    # Every named body is placed, meshless ones too, for the CAD they carry (ADR-838).
    names = {model.body(b).name for b in range(1, model.nbody)}
    assert set(trace["frames"][0]["component_placements"]) == names and meshes < names
    chest = (tmp_path / "c_chest_frame.stl").read_bytes()
    assert len(chest) == 84 + 50 * int.from_bytes(chest[80:84], "little") == 84 + 50 * 24
