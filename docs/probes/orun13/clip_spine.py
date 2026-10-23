"""orun13 B1: does the bundled gallop clip bend j_spine2 with j_spine? usage: clip_spine.py TASK.json MODEL.xml"""
import json, sys, numpy as np, mujoco
t = json.load(open(sys.argv[1])); m = mujoco.MjModel.from_xml_path(sys.argv[2]); d = mujoco.MjData(m)
r = t['reference']; J = r['joints']
a = np.asarray(r['joint_angles_rad'], float)
i1, i2 = J.index('j_spine'), J.index('j_spine2')
print('clip shape', a.shape)
print('spine  deg', np.round(np.degrees(a[:, i1]), 2))
print('spine2 deg', np.round(np.degrees(a[:, i2]), 2))
print('max |spine2-spine| deg', np.degrees(np.abs(a[:, i2]-a[:, i1]).max()), 'range', np.degrees(np.ptp(a[:, i1])))
# stand height: keyframe 'solved', settle 2 s with zero ctrl at keyframe targets
k = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_KEY, 'solved'); print('key', k)
mujoco.mj_resetDataKeyframe(m, d, k)
bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'c_chest_frame')
mujoco.mj_forward(m, d); print('keyframe chest z mm', d.xpos[bid][2]*1000)
