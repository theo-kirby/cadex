# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Independently compare the probe's subtree motion to accepted MJCF kinematics.

Usage: pixi run python docs/probes/ot7/sweep/pose_witness.py PROJECT OUT
No dynamics steps, contacts, script execution or project mutation.
"""
import json
import math
import sys
from pathlib import Path

import mujoco
import numpy as np

from probe import samples, snapshot, STEP

project, out = map(Path, sys.argv[1:])
accepted, staging, outputs = snapshot(project)
model = mujoco.MjModel.from_xml_path(str(staging / 'outputs/finch_model-model.xml'))
data = mujoco.MjData(model)
key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, 'solved')
assert key >= 0
links = {n: o for n, o in outputs.items() if o['type'] == 'component_link'}
poses = {n: np.array(o['solved_placement_matrix']).reshape(4, 4) for n, o in links.items()}
receipt = {'revision': accepted['revision'], 'step_degrees': STEP, 'joints': []}
for name, output in outputs.items():
    if output['type'] != 'joint' or not output['assembly_data'].get('angle_limits_degrees'):
        continue
    # The exact-solid receipt supplies the subtree actually moved by that sweep.
    measured = json.loads((out / f'{name}.json').read_text())
    joint = output['assembly_data']
    first = joint['connectors'][0]
    assert first['component_output'] not in measured['moving_components']
    frame = poses[first['component_output']] @ np.array(first['local_frame']['matrix']).reshape(4, 4)
    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
    assert joint_id >= 0 and model.jnt_type[joint_id] == mujoco.mjtJoint.mjJNT_HINGE
    address = model.jnt_qposadr[joint_id]
    assert abs(math.degrees(model.key_qpos[key, address]) - measured['initial_degrees']) < 1e-7
    error_mm = error_rotation = displacement = 0.0
    for value in samples(*joint['angle_limits_degrees'], STEP):
        mujoco.mj_resetDataKeyframe(model, data, key)
        data.qpos[address] = math.radians(value)
        mujoco.mj_forward(model, data)
        angle = math.radians(value - measured['initial_degrees'])
        c, s = math.cos(angle), math.sin(angle)
        rotation = np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
        delta = frame @ rotation @ np.linalg.inv(frame)
        for n in links:
            expected = delta @ poses[n] if n in measured['moving_components'] else poses[n]
            body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, n)
            assert body > 0
            error_mm = max(error_mm, float(np.max(np.abs(expected[:3, 3] - data.xpos[body] * 1000))))
            error_rotation = max(error_rotation, float(np.max(np.abs(expected[:3, :3] - data.xmat[body].reshape(3, 3)))))
            displacement = max(displacement, float(np.linalg.norm(expected[:3, 3] - poses[n][:3, 3])))
    assert error_mm < 1e-4 and error_rotation < 1e-6, (name, error_mm, error_rotation)
    receipt['joints'].append({'joint': name, 'maximum_position_error_mm': error_mm,
                              'maximum_rotation_matrix_error': error_rotation,
                              'maximum_component_origin_travel_mm': displacement})
(out / 'pose-witness.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
