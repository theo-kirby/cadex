"""orun19 S2: does the deterministic policy run faster than the noisy one it was rewarded as?

Builds the trainer's own environment (``training/cadex_train.build_environment``)
from a run's bundle, plays a checkpoint's actor for one 500-step episode
twice from the same keys -- once deterministic (what the engine judges), once
with the container's recorded exploration noise added before the tanh (what
PPO sampled and was rewarded for) -- and reports, per environment, the mean
``comv_x`` (the speed ``track_speed`` reads) over the last 2 s against the
command it was asked.

Run on the CPU (the GPU is the trainer's)::

    CUDA_VISIBLE_DEVICES= JAX_PLATFORMS=cpu ~/cadex-train-venv/bin/python \\
        docs/probes/orun19/noise_speed.py RUN_TRAIN_DIR CHECKPOINT [--envs 32]

``RUN_TRAIN_DIR`` holds ``<name>-task.json`` and ``cat_model-model.xml``;
they are copied into a scratch ``root/outputs/`` so ``load_bundle`` resolves
the model the way it does for a training run.
"""

from __future__ import annotations

import argparse
import shutil
import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "training"))
import cadex_train as CT  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("train_dir", type=Path)
    ap.add_argument("checkpoint", type=Path)
    ap.add_argument("--envs", type=int, default=32)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--noise-scale", type=float, nargs="+", default=[0.0, 1.0])
    args = ap.parse_args()

    import jax
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx
    import numpy as np

    task_file = next(args.train_dir.glob("*-task.json"))
    scratch = Path(tempfile.mkdtemp(prefix="noise_speed_"))
    (scratch / "outputs").mkdir()
    shutil.copy(task_file, scratch / "outputs" / task_file.name)
    shutil.copy(args.train_dir / "cat_model-model.xml", scratch / "outputs" / "cat_model-model.xml")
    bundle = CT.load_bundle(str(scratch / "outputs" / task_file.name), CT.globals_for(jnp))
    options = CT.arguments([str(scratch / "outputs" / task_file.name), "--out", str(scratch / "x.cxpolicy")])
    CT.match_engine_actuator_derivative(mujoco, jax, jnp)
    env = CT.build_environment(bundle, options, count=args.envs, seed=args.seed,
                               jax=jax, jnp=jnp, np=np, mujoco=mujoco, mjx=mjx)

    header, weights = (lambda d: (d["header"], d["weights"]))(
        CT.decode_policy(args.checkpoint.read_bytes()))
    shapes = [(int(a), int(b)) for a, b in header["network"]["layers"]]
    flat = np.asarray(weights, dtype=np.float32)
    layers, cursor = [], 0
    for inputs, outputs in shapes:
        w = flat[cursor:cursor + inputs * outputs].reshape(inputs, outputs); cursor += inputs * outputs
        b = flat[cursor:cursor + outputs]; cursor += outputs
        layers.append((jnp.asarray(w), jnp.asarray(b)))
    activation = str(header["network"].get("activation") or "tanh")
    mean = jnp.asarray(header["normaliser"]["mean"], dtype=jnp.float32)
    std = np.asarray(header["normaliser"]["std"], dtype=np.float32)
    std = jnp.asarray(np.where(std == 0.0, 1.0, std))
    sigma = jnp.exp(jnp.asarray(header["exploration"]["log_std"], dtype=jnp.float32))

    names = list(env.names)
    i_v, i_cmd = names.index("comv_x"), names.index("cmd")
    steps = int(env.horizon) if getattr(env, "horizon", None) else 500
    window = int(round(2.0 / float(bundle["task"]["episode"]["control_interval_s"])))

    def episode(noise_scale):
        def one(carry, key):
            state, alive = carry
            raw = CT.forward(jnp, layers, (state.obs["state"] - mean) / std, activation=activation)
            raw = raw + noise_scale * sigma * jax.random.normal(key, raw.shape)
            nxt = env.step(state, jnp.tanh(raw))
            seen = state.obs["privileged_state"]
            return (nxt, alive * (1.0 - nxt.done)), (seen[:, i_v], seen[:, i_cmd], alive)

        state = env.reset(jax.random.PRNGKey(args.seed))
        keys = jax.random.split(jax.random.PRNGKey(args.seed + 1), steps)
        _, (v, cmd, alive) = jax.lax.scan(one, (state, jnp.ones((args.envs,))), keys)
        return v, cmd, alive

    jitted = jax.jit(episode, static_argnums=0)

    def run(scale):
        return tuple(np.asarray(x) for x in jitted(scale))
    results = {}
    for scale in args.noise_scale:
        v, cmd, alive = run(scale)
        whole = alive[-1] > 0  # lived the whole episode, never reset
        ratio = v[-window:].mean(axis=0) / cmd[-1]
        results[scale] = (ratio, cmd[-1], whole)
        print(f"noise x{scale:g}: whole episodes {int(whole.sum())}/{args.envs}; "
              f"last-2-s comv_x / cmd median {statistics.median(ratio[whole].tolist()):.3f} "
              f"(min {ratio[whole].min():.3f} / max {ratio[whole].max():.3f})", flush=True)
    base = results[args.noise_scale[0]]
    print("cmd mm/s | " + " | ".join(f"x{s:g}" for s in args.noise_scale))
    order = np.argsort(base[1])
    for e in order:
        cells = [f"{results[s][0][e]:.3f}{'' if results[s][2][e] else '*'}" for s in args.noise_scale]
        print(f"{base[1][e]:7.0f} | " + " | ".join(cells))
    print("* = reset within the episode (fell or terminated); left out of the medians")


if __name__ == "__main__":
    main()
