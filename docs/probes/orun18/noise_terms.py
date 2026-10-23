"""Price b1-s1's regularisers under exploration noise: stock MuJoCo, CPU."""
import json, sys, numpy as np, mujoco
bundle = json.load(open(sys.argv[1])); xml = sys.argv[2]; sigma = float(sys.argv[3])
m = mujoco.MjModel.from_xml_path(xml); d = mujoco.MjData(m)
k = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_KEY, bundle["episode"]["reset_keyframe"])
rng = np.random.default_rng(0)
acts = bundle["actions"]
aid = [mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, a["actuator"]) for a in acts]
assert min(aid) >= 0, aid
jid = [m.actuator_trnid[i, 0] for i in aid]
rated = np.array([a.get("rated_effort", 1.0) for a in acts])
lo = np.array([a["low"] for a in acts]); hi = np.array([a["high"] for a in acts])
mid, half = (lo + hi) / 2, (hi - lo) / 2
out = {"torque": [], "energy": [], "action_rate": [], "steps": []}
for ep in range(20):
    mujoco.mj_resetDataKeyframe(m, d, k); mujoco.mj_forward(m, d)
    prev = d.ctrl[aid].copy() * 180 / np.pi
    tq = en = ar = 0.0
    for step in range(100):
        cmd = np.clip(mid + half * sigma * rng.standard_normal(len(acts)), lo, hi)
        d.ctrl[aid] = np.deg2rad(cmd)
        for _ in range(bundle["episode"]["solver_steps_per_action"]):
            mujoco.mj_step(m, d)
        tau = d.actuator_force[aid] * 1000.0             # N*m -> N*mm
        dq = np.rad2deg(d.qvel[[m.jnt_dofadr[j] for j in jid]])
        rate = (cmd - prev) / bundle["episode"]["control_interval_s"]; prev = cmd
        drv = [i for i, a in enumerate(acts) if not a["joint"].startswith("j_tail")]
        eff = drv + [i for i, a in enumerate(acts) if a["joint"] == "j_tail1"]
        out["torque"].append(np.mean((tau[eff] / rated[eff]) ** 2))
        out["energy"].append(np.sum(np.abs(dq[eff] * tau[eff])) / 57295780)
        out["action_rate"].append(np.sum((rate[drv] / 600) ** 2))
for key in ("torque", "energy", "action_rate"):
    v = np.array(out[key]); print(f"{key:12s} mean {v.mean():8.3f}  median {np.median(v):8.3f}  p90 {np.percentile(v, 90):8.3f}")
