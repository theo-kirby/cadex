"""orun13 B1: hold the keyframe pose for 3 s on every drive; the chest frame height (scan_4) it settles to. usage: stand_hold.py MODEL.xml"""
import sys, numpy as np, mujoco
m = mujoco.MjModel.from_xml_path(sys.argv[1]); d = mujoco.MjData(m)
mujoco.mj_resetDataKeyframe(m, d, 0)
for i in range(m.nu):
    j = m.actuator_trnid[i, 0]
    d.ctrl[i] = d.qpos[m.jnt_qposadr[j]] if m.actuator_trntype[i] == 0 else 0.0
bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'c_chest_frame')
mujoco.mj_forward(m, d)
print('free qpos z', d.qpos[2]*1000, 'chest z', d.xpos[bid][2]*1000, 'nkey', m.nkey, [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_KEY, k) for k in range(m.nkey)])
for g in range(m.ngeom):
    if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE: print('plane', mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g), m.geom_pos[g])
zs = []
for k in range(int(3.0 / m.opt.timestep)):
    mujoco.mj_step(m, d)
    if k % 250 == 0: zs.append(round(d.xpos[bid][2]*1000, 1))
pitch = np.degrees(np.arcsin(2*(d.qpos[3]*d.qpos[5]-d.qpos[4]*d.qpos[6])))
print('chest z over 3 s', zs, 'nan', np.isnan(d.qpos).any(), 'pitch deg', round(pitch, 1))
