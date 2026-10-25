import sys, numpy as np, mujoco
m = mujoco.MjModel.from_xml_path(sys.argv[1])
d = mujoco.MjData(m)
mujoco.mj_resetDataKeyframe(m, d, 0)
if m.nu and m.nkey and m.key_ctrl.size: d.ctrl[:] = m.key_ctrl[0]
steps = int(3.0 / m.opt.timestep)
z0 = d.qpos[2]
for _ in range(steps):
    mujoco.mj_step(m, d)
nan = not np.all(np.isfinite(d.qpos))
mujoco.mj_forward(m, d)
mass = float(m.body_subtreemass[0]) if m.body_subtreemass[0] > 0 else float(m.body_mass.sum())
g = 9.81 * float(m.body_mass.sum())
fz_ground = 0.0; names = {}
for i in range(d.ncon):
    c = d.contact[i]
    f = np.zeros(6); mujoco.mj_contactForce(m, d, i, f)
    g1, g2 = c.geom1, c.geom2
    other = g2 if m.geom_bodyid[g1] == 0 else (g1 if m.geom_bodyid[g2] == 0 else None)
    if other is None: continue
    fn = abs(f[0]); fz_ground += fn
    nm = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, other) or f"geom{other}"
    names[nm] = names.get(nm, 0.0) + fn
print("timestep", m.opt.timestep, "steps", steps, "NaN", nan, "root z", round(z0, 4), "->", round(float(d.qpos[2]), 4), "mass", round(float(m.body_mass.sum()), 3))
print("ground normal force", round(fz_ground, 1), "N of weight", round(g, 1))
for k, v in sorted(names.items(), key=lambda kv: -kv[1]): print("  ", k, round(v, 1))
