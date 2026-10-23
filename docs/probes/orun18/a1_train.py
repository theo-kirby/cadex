"""orun18 A1: train Playground's Go1JoystickFlatTerrain from its published PPO config.

Runs from ~/playground-venv (playground 0.2.0, see SOURCES.md), never from the
Cadex venvs. Our own launcher, written against Playground's public API
(registry, wrapper, config.locomotion_params): the repository's
learning/train_jax_ppo.py is not in the wheel and is not copied here.

One deviation from the env's default config, recorded in the A1 report:
impl="jax" (MJX), not the 0.2.0 default "warp", so the physics backend is the
one Cadex's trainer uses. Everything else is brax_ppo_config(env) as shipped.

    ~/playground-venv/bin/python a1_train.py --out ~/orun18/a1 [--timesteps N]

Writes progress.jsonl (one line per eval, wall time and env steps), config.json
and params.pkl (brax.io.model.save_params) under --out.
"""
import argparse
import functools
import json
import os
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--env", default="Go1JoystickFlatTerrain")
    ap.add_argument("--impl", default="jax")
    ap.add_argument("--timesteps", type=int, default=None,
                    help="override num_timesteps (smoke tests only)")
    ap.add_argument("--num-evals", type=int, default=None)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    out = os.path.expanduser(args.out)
    os.makedirs(out, exist_ok=True)

    t_import = time.time()
    from brax.io import model as brax_model
    from brax.training.agents.ppo import networks as ppo_networks
    from brax.training.agents.ppo import train as ppo
    from mujoco_playground import registry, wrapper
    from mujoco_playground.config import locomotion_params

    env_cfg = registry.get_default_config(args.env)
    env_cfg.impl = args.impl
    env = registry.load(args.env, config=env_cfg)
    eval_env = registry.load(args.env, config=env_cfg)
    ppo_params = locomotion_params.brax_ppo_config(args.env, args.impl)
    if args.timesteps is not None:
        ppo_params.num_timesteps = args.timesteps
    if args.num_evals is not None:
        ppo_params.num_evals = args.num_evals

    with open(os.path.join(out, "config.json"), "w") as f:
        json.dump({"env": args.env, "seed": args.seed,
                   "env_config": env_cfg.to_dict(),
                   "ppo": ppo_params.to_dict()}, f, indent=1, default=str)

    params = dict(ppo_params)
    net = params.pop("network_factory")
    network_factory = functools.partial(ppo_networks.make_ppo_networks, **net)
    log = open(os.path.join(out, "progress.jsonl"), "a")
    t0 = [None]

    def progress(step, metrics):
        now = time.time()
        if t0[0] is None:
            t0[0] = now
        row = {"t": now, "wall_s": now - t_import, "since_first_eval_s": now - t0[0],
               "env_steps": int(step)}
        row.update({k: float(v) for k, v in metrics.items()
                    if k in ("eval/episode_reward", "eval/episode_reward_std",
                             "eval/avg_episode_length", "training/sps",
                             "eval/walltime", "training/walltime")
                    or k.startswith("eval/episode_reward/")})
        log.write(json.dumps(row) + "\n")
        log.flush()
        print(json.dumps(row), flush=True)

    make_inference_fn, policy_params, _ = ppo.train(
        environment=env,
        eval_env=eval_env,
        wrap_env_fn=wrapper.wrap_for_brax_training,
        network_factory=network_factory,
        randomization_fn=registry.get_domain_randomizer(args.env),
        progress_fn=progress,
        seed=args.seed,
        **params,
    )
    brax_model.save_params(os.path.join(out, "params.pkl"), policy_params)
    with open(os.path.join(out, "done.json"), "w") as f:
        json.dump({"total_wall_s": time.time() - t_import,
                   "env_steps": int(ppo_params.num_timesteps)}, f)
    print("saved", os.path.join(out, "params.pkl"), flush=True)


if __name__ == "__main__":
    main()
