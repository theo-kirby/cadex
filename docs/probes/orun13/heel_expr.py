"""orun13 (O2, O5): heel_pitch's per-leg metatarsus angle against each rigid hind sole's real pitch, over the clip.

    CUDA_VISIBLE_DEVICES= ~/cadex-train-venv/bin/python docs/probes/orun13/heel_expr.py RUN/train/gallop-task.json

Sets the model to each of the bundle's clip samples (``reset_qpos``), reads the
observed channels the trainer reads (``reward_terms.channel_vector``), and
evaluates heel_pitch's inner angle for each leg (chest pitch + 2 q_spine
+ hip - knee + hock + 63.9, the right leg's joints sign-flipped) next to the
paw body's world pitch from MuJoCo. Prints both per sample, with the clip's
``ref_lh_down`` / ``ref_rh_down`` stance flags, and the offset per leg. A
constant 63.9 on both legs means the reward reads the left and right soles
alike. Writes nothing.
"""
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mujoco
import numpy as np
import reward_terms as rt
task, model = rt.load(Path(sys.argv[1]))
comp = rt.compiled(task)
table, names, rewards, terms = comp
data = mujoco.MjData(model)
tr = task["tracking"]
def m_expr(v, side):
    body = 57.2958*math.asin(2*(v['imu_qw']*v['imu_qy']-v['imu_qx']*v['imu_qz']))
    if side=='l': return body + 2*v['q_spine'] + v['q_hip_l'] - v['q_knee_l'] + v['q_hock_l'] + 63.9
    return body + 2*v['q_spine'] - v['q_hip_r'] + v['q_knee_r'] - v['q_hock_r'] + 63.9
def wpitch(body):
    b = model.body(body).id
    R = data.xmat[b].reshape(3,3); x = R[:,0]
    return math.degrees(math.atan2(-x[2], x[0]))
rows=[]
for s in range(int(tr["samples"])):
    data.qpos[:] = tr["reset_qpos"][s]; data.qvel[:] = tr["reset_qvel"][s]
    mujoco.mj_forward(model, data)
    vec = rt.channel_vector(task, model, data, 0, s)
    v = {n: float(vec[i]) for i, n in enumerate(names)}
    rows.append((s, m_expr(v,'l'), wpitch('c_paw_hl'), m_expr(v,'r'), wpitch('c_paw_hr'),
                 v.get('ref_lh_down'), v.get('ref_rh_down'), v['q_spine']))
print("s  mL  pawL  mR  pawR  refLH refRH  q_spine")
for r in rows: print(" ".join("%7.2f"%x if isinstance(x,float) else str(x) for x in r))
a=np.array([r[1:5] for r in rows])
print("offset L (m - paw):", np.round(a[:,0]-a[:,1],2))
print("offset R (m - paw):", np.round(a[:,2]-a[:,3],2))
