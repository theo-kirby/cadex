"""G3 probe: a frozen actor (or random / zero actions) in the trainer's own MJX
environment on a composed course, and the same actor in stock MuJoCo through
the engine's rollout_policy on the same pooled courses."""
import json, sys, time, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src" / "Mod" / "cadex"))
sys.path.insert(0, str(ROOT / "training"))
import numpy as np
import cadex_train as T

def mjx_probe(bundle_path, actor, envs, steps, seed=0):
    import jax, jax.numpy as jnp, mujoco
    from mujoco import mjx
    bundle = T.load_bundle(bundle_path, T.globals_for(jnp))
    options = T.arguments([bundle_path, "--out", "/tmp/g3probe.cxpolicy", "--envs", str(envs),
                           "--command-slew-deg", "15"])
    env = T.build_environment(bundle, options, count=envs, seed=seed, jax=jax, jnp=jnp, np=np,
                              mujoco=mujoco, mjx=mjx)
    act = None
    if actor not in ("random", "zero"):
        pol = T.decode_policy(Path(actor).read_bytes())
        h = pol["header"]; net = h["network"]
        shapes = [(int(a), int(b)) for a, b in net["layers"]]
        params = [(jnp.asarray(w, jnp.float32), jnp.asarray(b, jnp.float32))
                  for w, b in T.unflatten_parameters(np, pol["weights"], shapes)]
        mean = jnp.asarray(h["normaliser"]["mean"], jnp.float32)
        std = jnp.asarray(h["normaliser"]["std"], jnp.float32)
        activation = str(net.get("activation") or "tanh")
        assert len(h["normaliser"]["mean"]) == env.observation_size["state"][0], "actor inputs differ"
        act = lambda obs, key: jnp.tanh(T.forward(jnp, params, (obs - mean) / std, activation=activation))
    elif actor == "random":
        act = lambda obs, key: jax.random.uniform(key, (envs, env.action_size), minval=-1.0, maxval=1.0)
    else:
        act = lambda obs, key: jnp.zeros((envs, env.action_size))
    reset = jax.jit(env.reset)
    @jax.jit
    def step(state, key):
        return env.step(state, act(state.obs["state"], key))
    key = jax.random.PRNGKey(seed)
    t0 = time.time(); state = reset(key); state = step(state, key)
    jax.block_until_ready(state.obs["state"]); compile_s = time.time() - t0
    first_end = np.full(envs, -1); first_term = np.zeros(envs, bool)
    nonfinite = 0; terminated = 0; episodes = 0; finite_state = True
    t0 = time.time()
    for k in range(1, steps):
        key, sub = jax.random.split(key)
        state = step(state, sub)
        info = state.info
        nf = np.asarray(info["nonfinite"]); te = np.asarray(info["terminated"]); dn = np.asarray(state.done)
        nonfinite += int(nf.sum()); terminated += int(te.sum()); episodes += int(dn.sum())
        new = (first_end < 0) & (dn > 0)
        first_end[new] = k; first_term[new] = te[new] > 0
    jax.block_until_ready(state.obs["state"]); run_s = time.time() - t0
    q = np.asarray(state.pipeline_state.qpos)
    return {"envs": envs, "steps": steps, "compile_s": round(compile_s, 1),
            "env_steps_per_s": round(envs * (steps - 1) / run_s), "nonfinite_events": nonfinite,
            "terminated_episodes": terminated, "ended_episodes": episodes,
            "first_episode_tipped": int(first_term.sum()),
            "first_episode_tip_rate": round(float(first_term.sum()) / envs, 3),
            "final_state_finite": bool(np.isfinite(q).all())}

def stock_probe(bundle_path, actor, horizon, episodes):
    import CadexDynamics as D
    task = json.loads(Path(bundle_path).read_text())
    xml = (Path(bundle_path).parent / Path(task["model"]["path"]).name).read_bytes()
    container = D.decode_policy(Path(actor).read_bytes())
    terrain = task.get("terrain")
    task = {**task, "episode": {**task["episode"], "max_steps": horizon}}
    rows = []
    for k in range(episodes):
        model = D.load_model(xml)
        played = task
        if terrain and terrain.get("pool"):
            course = {key: v for key, v in terrain.items() if key != "pool"}
            entry = terrain["pool"][k % len(terrain["pool"])]
            feats = [D._terrain_feature(f, i, "g3") for i, f in enumerate(entry["features"])]
            built = D.terrain_boxes(feats, terrain["x_range_mm"], terrain["y_range_mm"])
            assert len(built["boxes"]) == entry["boxes"]
            course.update(features=feats, boxes=built["boxes"], domes=built["domes"],
                          lowest_mm=built["lowest_mm"], highest_mm=built["highest_mm"])
            course["course"] = {"pool": k % len(terrain["pool"])}
            D.place_terrain_course(model, course)
            played = {**task, "terrain": course}
        run = D.rollout_policy(model, played, container, components=[], frames_per_second=int(task["episode"]["control_hz"]),
                               seed=1000 + k, context="g3 probe")
        ep = run["episode"]
        rows.append({"termination": ep.get("termination"), "terminated_step": ep.get("terminated_step"),
                     "steps": ep.get("step_count")})
    tipped = sum(1 for r in rows if r["termination"])
    return {"episodes": episodes, "horizon": horizon, "tipped": tipped,
            "tip_rate": round(tipped / episodes, 3),
            "rows": rows[:6], "reasons": sorted({r["termination"] for r in rows if r["termination"]})}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["mjx", "stock"]); p.add_argument("bundle"); p.add_argument("actor")
    p.add_argument("--envs", type=int, default=256); p.add_argument("--steps", type=int, default=200)
    p.add_argument("--episodes", type=int, default=32)
    a = p.parse_args()
    out = (mjx_probe(a.bundle, a.actor, a.envs, a.steps) if a.mode == "mjx"
           else stock_probe(a.bundle, a.actor, a.steps, a.episodes))
    print(json.dumps({"mode": a.mode, "bundle": a.bundle, "actor": Path(a.actor).name, **out}))
