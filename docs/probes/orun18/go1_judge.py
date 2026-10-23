"""orun18 D3: one yardstick for both Go1 policies (A1 Playground, A2 Cadex).

The referee is stock MuJoCo on the CPU, outside both trainers: each policy is
loaded through an adapter that gives the referee its MjModel, its control
period, how it turns a state into joint targets, and nothing else. The
referee owns the seeds, the commands, the clock and every measurement.

Per command (forward speed, body frame; lateral and yaw commanded 0) and per
seed, one episode of --seconds from the robot's home pose with a seeded
perturbation (joint offsets U(-0.05, 0.05) rad, base velocity U(-0.2, 0.2)).
It reports:

- tracked speed: mean forward body-frame speed over the last 2 s window,
  and the best 2 s window; lateral drift speed and yaw rate over the last
  window;
- falls: trunk z-axis below 0.5 (tilted past 60 deg) or trunk below 0.12 m,
  which ends the episode; a fallen seed's window is not counted;
- torque: per actuator, RMS and peak of actuator_force over its forcerange
  limit, and the share of frames within 1% of the limit.

    ~/playground-venv/bin/python -I go1_judge.py playground ~/orun18/a1 \
        --out ~/orun18/a1/judge.json [--trace-dir DIR]

Adapters: `playground` (a1_train.py's params.pkl).
"""
import argparse
import json
import os
import sys

import mujoco
import numpy as np

COMMANDS = (0.5, 1.0, 1.5)  # m/s; 1.5 is the top of Playground's vx range
SEEDS = tuple(range(10))
WINDOW_S = 2.0
FALL_UPZ = 0.5
FALL_HEIGHT = 0.12


class PlaygroundGo1:
    """a1_train.py's policy on Playground's own Go1 model (noise off)."""

    def __init__(self, run_dir):
        from brax.io import model as brax_model
        from brax.training.acme import running_statistics
        from brax.training.agents.ppo import networks as ppo_networks
        from mujoco_playground import registry
        import jax

        cfg = json.load(open(os.path.join(run_dir, "config.json")))
        env_cfg = registry.get_default_config(cfg["env"])
        env_cfg.impl = cfg["env_config"]["impl"]
        env = registry.load(cfg["env"], config=env_cfg)
        self.mj_model = env.mj_model  # timestep, Kp, Kd as trained
        self.n_substeps = int(round(env_cfg.ctrl_dt / env_cfg.sim_dt))
        self.ctrl_dt = env_cfg.ctrl_dt
        self.action_scale = env_cfg.action_scale
        self.default_pose = np.array(self.mj_model.keyframe("home").qpos[7:])
        self.home_qpos = np.array(self.mj_model.keyframe("home").qpos)
        self.trunk = self.mj_model.body("trunk").id
        self.imu = self.mj_model.site("imu").id
        net = cfg["ppo"]["network_factory"]
        nets = ppo_networks.make_ppo_networks(
            {"state": (48,), "privileged_state": (123,)}, self.mj_model.nu,
            preprocess_observations_fn=running_statistics.normalize,
            policy_hidden_layer_sizes=tuple(net["policy_hidden_layer_sizes"]),
            value_hidden_layer_sizes=tuple(net["value_hidden_layer_sizes"]),
            policy_obs_key=net["policy_obs_key"],
            value_obs_key=net["value_obs_key"])
        params = brax_model.load_params(os.path.join(run_dir, "params.pkl"))
        policy = ppo_networks.make_inference_fn(nets)(params, deterministic=True)
        self._policy = jax.jit(policy)
        self._key = jax.random.PRNGKey(0)
        self._jnp = jax.numpy
        self.source = os.path.join(run_dir, "params.pkl")

    def _sensor(self, data, name):
        s = self.mj_model.sensor(name)
        return data.sensordata[s.adr[0]:s.adr[0] + s.dim[0]]

    def reset(self):
        self.last_act = np.zeros(self.mj_model.nu)

    def targets(self, data, command):
        gravity = data.site_xmat[self.imu].reshape(3, 3).T @ np.array([0, 0, -1.0])
        state = np.concatenate([
            self._sensor(data, "local_linvel"), self._sensor(data, "gyro"),
            gravity, data.qpos[7:] - self.default_pose, data.qvel[6:],
            self.last_act, command]).astype(np.float32)
        obs = {"state": self._jnp.asarray(state)[None],
               "privileged_state": self._jnp.zeros((1, 123), np.float32)}
        act, _ = self._policy(obs, self._key)
        act = np.asarray(act[0], dtype=np.float64)
        self.last_act = act
        return self.default_pose + act * self.action_scale


ADAPTERS = {"playground": PlaygroundGo1}


def episode(pol, command_vx, seed, seconds, trace=None):
    m = pol.mj_model
    d = mujoco.MjData(m)
    rng = np.random.default_rng(seed)
    d.qpos[:] = pol.home_qpos
    d.qpos[7:] += rng.uniform(-0.05, 0.05, m.nq - 7)
    d.qvel[:6] = rng.uniform(-0.2, 0.2, 6)
    d.ctrl[:] = d.qpos[7:]
    mujoco.mj_forward(m, d)
    pol.reset()
    command = np.array([command_vx, 0.0, 0.0])
    lo, hi = m.actuator_forcerange[:, 0], m.actuator_forcerange[:, 1]
    limit = np.maximum(np.abs(lo), np.abs(hi))
    steps = int(round(seconds / pol.ctrl_dt))
    vfwd, vlat, yaw, forces, qpos = [], [], [], [], []
    fell_at = None
    for k in range(steps):
        d.ctrl[:] = pol.targets(d, command)
        for _ in range(pol.n_substeps):
            mujoco.mj_step(m, d)
            forces.append(d.actuator_force.copy())
        if not np.all(np.isfinite(d.qpos)):
            fell_at = k * pol.ctrl_dt
            break
        R = d.xmat[pol.trunk].reshape(3, 3)
        v_body = R.T @ d.qvel[:3]  # free joint: world linear velocity
        vfwd.append(v_body[0])
        vlat.append(v_body[1])
        yaw.append(d.qvel[5])
        if trace is not None:
            qpos.append(d.qpos.copy())
        if R[2, 2] < FALL_UPZ or d.xpos[pol.trunk][2] < FALL_HEIGHT:
            fell_at = (k + 1) * pol.ctrl_dt
            break
    n = int(round(WINDOW_S / pol.ctrl_dt))
    vf = np.array(vfwd)
    out = {"seed": seed, "fell": fell_at is not None, "fell_at_s": fell_at}
    if fell_at is None and len(vf) >= n:
        c = np.convolve(vf, np.ones(n) / n, mode="valid")
        out.update(last2s=float(vf[-n:].mean()), best2s=float(c.max()),
                   lat_last2s=float(np.mean(vlat[-n:])),
                   yaw_last2s=float(np.mean(yaw[-n:])))
    f = np.abs(np.array(forces))
    out["rms_over_limit"] = (np.sqrt((f ** 2).mean(0)) / limit).tolist()
    out["peak_over_limit"] = (f.max(0) / limit).tolist()
    out["at_clamp_share"] = (f >= 0.99 * limit).mean(0).tolist()
    if trace is not None:
        np.save(os.path.join(trace, f"cmd{command_vx:.2f}_seed{seed}.npy"), np.array(qpos))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("adapter", choices=sorted(ADAPTERS))
    ap.add_argument("source")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=8.0)
    ap.add_argument("--commands", type=float, nargs="+", default=list(COMMANDS))
    ap.add_argument("--trace-dir", default=None)
    args = ap.parse_args()
    pol = ADAPTERS[args.adapter](os.path.expanduser(args.source))
    if args.trace_dir:
        os.makedirs(args.trace_dir, exist_ok=True)
    names = [pol.mj_model.actuator(i).name for i in range(pol.mj_model.nu)]
    result = {"adapter": args.adapter, "source": pol.source, "seeds": list(SEEDS),
              "seconds": args.seconds, "window_s": WINDOW_S,
              "actuators": names, "commands": {}}
    for vx in args.commands:
        eps = [episode(pol, vx, s, args.seconds, args.trace_dir) for s in SEEDS]
        ok = [e for e in eps if not e["fell"]]
        rms = np.array([e["rms_over_limit"] for e in eps]).max(0)
        peak = np.array([e["peak_over_limit"] for e in eps]).max(0)
        clamp = np.array([e["at_clamp_share"] for e in eps]).mean(0)
        summary = {
            "falls": len(eps) - len(ok),
            "last2s_mean": float(np.mean([e["last2s"] for e in ok])) if ok else None,
            "last2s_min": float(np.min([e["last2s"] for e in ok])) if ok else None,
            "best2s_max": float(np.max([e["best2s"] for e in ok])) if ok else None,
            "lat_last2s_mean": float(np.mean([e["lat_last2s"] for e in ok])) if ok else None,
            "yaw_last2s_mean": float(np.mean([e["yaw_last2s"] for e in ok])) if ok else None,
            "worst_rms_over_limit": [names[int(rms.argmax())], float(rms.max())],
            "worst_peak_over_limit": [names[int(peak.argmax())], float(peak.max())],
            "at_clamp_share_max": [names[int(clamp.argmax())], float(clamp.max())],
        }
        result["commands"][f"{vx:.2f}"] = {"summary": summary, "episodes": eps}
        s = summary
        print(f"cmd {vx:.2f}: falls {s['falls']}/10  last2s {s['last2s_mean']}  "
              f"min {s['last2s_min']}  rms {s['worst_rms_over_limit']}  "
              f"peak {s['worst_peak_over_limit']}  clamp {s['at_clamp_share_max']}",
              flush=True)
    with open(os.path.expanduser(args.out), "w") as f:
        json.dump(result, f, indent=1)


if __name__ == "__main__":
    sys.exit(main())
