"""Do the trainer and the engine's rollout observe the same numbers?  (ot11 R3)

Both read a task's observation as ``sensordata[adr:adr+dim] * scale`` from
the same model file (``cadex_train.observe``, ``CadexDynamics.
observation_values``), after the step.  What could still differ is the
physics library underneath: the trainer computes ``sensordata`` in MJX and
the rollout in MuJoCo's C library.  This measures that difference over
states the mechanism actually reaches: it drives the model in MuJoCo with
random in-range commands from a random push, and at every sampled state
hands the same ``qpos``/``qvel``/``ctrl`` to ``mjx.forward`` and compares
every channel, scaled into the unit the task declares.

It also reports which frame each angular-velocity channel reads in (world
or body), since a gyro measures in its own frame.

Run from the training venv (``training/requirements.txt``), never pixi:

    python docs/probes/ot11/runner/obs_parity.py RUN/train --out receipt.json

``RUN/train`` holds the ``*-task.json`` bundle and ``*-model.xml`` that a
loop run trained on.  The receipt carries no path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def measure(train_dir: Path, *, episodes: int, steps: int, every: int, seed: int) -> dict:
    import jax
    import mujoco
    from mujoco import mjx
    import numpy as np

    (bundle,) = sorted(train_dir.glob("*-task.json"))
    (model_xml,) = sorted(train_dir.glob("*-model.xml"))
    task = json.loads(bundle.read_text(encoding="utf-8"))
    model = mujoco.MjModel.from_xml_path(str(model_xml))
    data = mujoco.MjData(model)
    forward = jax.jit(mjx.forward)
    mx = mjx.put_model(model)
    rng = np.random.default_rng(seed)
    low = np.array([float(a["low"]) * float(a["scale"]) for a in task["actions"]])
    high = np.array([float(a["high"]) * float(a["scale"]) for a in task["actions"]])
    index = np.array([int(a["index"]) for a in task["actions"]])

    worst: dict[str, dict] = {}
    frames: dict[str, dict] = {}
    states = 0
    for _ in range(episodes):
        if model.nkey:
            mujoco.mj_resetDataKeyframe(model, data, 0)
        else:
            mujoco.mj_resetData(model, data)
        data.qvel[:] = rng.normal(0.0, 0.5, model.nv)
        for step in range(steps):
            data.ctrl[index] = rng.uniform(low, high)
            mujoco.mj_step(model, data)
            if step % every:
                continue
            mujoco.mj_forward(model, data)
            reference = np.asarray(data.sensordata, dtype=float)
            trained = np.asarray(forward(mx, mjx.put_data(model, data)).sensordata, dtype=float)
            states += 1
            for record in task["observations"]:
                adr, dim, scale = int(record["adr"]), int(record["dim"]), float(record["scale"])
                row = worst.setdefault(record["name"], {
                    "role": str(record.get("role") or "policy"),
                    "grounded_sensor": record.get("grounded_sensor"),
                    "unit": record["unit"], "max_abs_diff": 0.0, "max_magnitude": 0.0})
                cut = slice(adr, adr + dim)
                row["max_abs_diff"] = max(row["max_abs_diff"],
                                          float(np.max(np.abs(reference[cut] - trained[cut])) * scale))
                row["max_magnitude"] = max(row["max_magnitude"],
                                           float(np.max(np.abs(reference[cut])) * scale))
                if record["kind"] == "component_angular_velocity":
                    # Judged at the most tilted state seen: upright, the two
                    # frames coincide and the question has no answer.
                    body = model.body(record["target"]).id
                    rotation = data.xmat[body].reshape(3, 3)
                    tilt = float(np.degrees(np.arccos(np.clip(rotation[2, 2], -1, 1))))
                    if tilt <= frames.get(record["name"], {}).get("tilt_deg", -1.0):
                        continue
                    world = data.cvel[body][:3]  # MuJoCo's com-based velocity: angular part, world frame
                    reading = reference[cut]
                    frames[record["name"]] = {
                        "target": record["target"],
                        "err_if_world_frame": float(np.max(np.abs(reading - world))),
                        "err_if_body_frame": float(np.max(np.abs(reading - rotation.T @ world))),
                        "tilt_deg": tilt,
                    }
    for name, row in frames.items():
        row["frame"] = "world" if row["err_if_world_frame"] < row["err_if_body_frame"] else "body"
    return {
        "schema": "cadex-ot11-obs-parity-v1",
        "task": task.get("label"),
        "task_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
        "model_sha256": hashlib.sha256(model_xml.read_bytes()).hexdigest(),
        "mujoco": mujoco.__version__,
        "jax_backend": jax.default_backend(),
        "states_compared": states,
        "settings": {"episodes": episodes, "steps": steps, "every": every, "seed": seed},
        "channels": worst,
        "angular_velocity_frames": frames,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("train_dir", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--every", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    receipt = measure(args.train_dir, episodes=args.episodes, steps=args.steps,
                      every=args.every, seed=args.seed)
    args.out.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({name: row["max_abs_diff"] for name, row in receipt["channels"].items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
