# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The throughput bench: env steps per second of any MJCF in MJX, holding its stand.

One env step is one control step (20 ms by default, Playground's and Cadex's
control dt), made of ``control_dt / timestep`` substeps of ``mjx.step``. Every
env starts at keyframe 0 with that keyframe's controls (the stand a Cadex
export solves, Playground's ``home``), or at ``qpos0`` with zero controls when
the model has no keyframe: a policy whose action is zero. The envs are batched
with ``jax.vmap`` and the control steps rolled with ``lax.scan`` in one jitted
call; the first call compiles, the timed call after it is the measurement.

``--timestep``, ``--iterations``, ``--ls-iterations`` and ``--integrator``
override the model's options before it goes to the GPU, so one cut can be
timed under each setting of ``cadex_training_model.LADDER`` (``Euler`` here
also switches Euler damping off, as the cut writes it).

    systemd-run --user --scope -p MemoryMax=30G \\
      ~/cadex-train-venv/bin/python training/cadex_train_bench.py MODEL.xml
        [--envs 2048,8192] [--steps 100] [--control-dt 0.02] [--integrator implicitfast]
        [--timestep S] [--iterations N] [--ls-iterations N] [--json OUT]

It prints one JSON object: the model's digest and tier, the options it ran
with, the MJX contact and constraint sizes, and per env count the compile
time, the timed wall time, env steps/s, and whether every env stayed finite
with the root's centre of mass above half its start height (a model that
explodes or falls is timed, but says so). Exits 0 only when every env
stayed finite. ``jax``, ``mujoco`` and ``numpy`` are imported inside
functions (ADR-084).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

INTEGRATORS = ("Euler", "RK4", "implicit", "implicitfast")  # mjtIntegrator's order


def substeps(control_dt: float, timestep: float) -> int:
    """Physics substeps per control step; the control dt must be a whole number of them."""

    n = round(control_dt / timestep)
    if n < 1 or abs(n * timestep - control_dt) > 1e-9:
        raise ValueError(f"control dt {control_dt} is not a whole number of {timestep} s timesteps")
    return n


def tier(text: str) -> str | None:
    """The ``cadex:tier`` a Cadex tool marked the model with, if any."""

    marks = [t.get("data") for t in ET.fromstring(text).iter("text") if t.get("name") == "cadex:tier"]
    return marks[0] if marks else None


def apply_options(m, *, timestep=None, iterations=None, ls_iterations=None, integrator=None) -> None:
    """Override the compiled model's solver options in place."""

    import mujoco as mj

    if timestep is not None:
        m.opt.timestep = timestep
    if iterations is not None:
        m.opt.iterations = iterations
    if ls_iterations is not None:
        m.opt.ls_iterations = ls_iterations
    if integrator is not None:
        m.opt.integrator = INTEGRATORS.index(integrator)
        eulerdamp = int(mj.mjtDisableBit.mjDSBL_EULERDAMP)
        if integrator == "Euler":
            m.opt.disableflags |= eulerdamp
        else:
            m.opt.disableflags &= ~eulerdamp


def root_body(m) -> int:
    """The first body on a free joint (the robot's root); body 1 when none is free."""

    import mujoco as mj

    for j in range(m.njnt):
        if m.jnt_type[j] == mj.mjtJoint.mjJNT_FREE:
            return int(m.jnt_bodyid[j])
    return 1


def bench(xml_path: Path, envs: list[int], steps: int = 100, control_dt: float = 0.02,
          **options) -> dict:
    """Measure the model at each env count."""

    import jax
    import jax.numpy as jnp
    import mujoco as mj
    from mujoco import mjx

    text = xml_path.read_text()
    m = mj.MjModel.from_xml_path(str(xml_path))
    apply_options(m, **options)
    n_sub = substeps(control_dt, m.opt.timestep)
    root = root_body(m)
    qpos = m.key_qpos[0] if m.nkey else m.qpos0
    ctrl = m.key_ctrl[0] if m.nkey else [0.0] * m.nu
    mx = mjx.put_model(m)
    d0 = mjx.make_data(mx).replace(qpos=jnp.asarray(qpos), ctrl=jnp.asarray(ctrl))
    d0 = mjx.forward(mx, d0)
    z0 = float(d0.subtree_com[root, 2])  # a Cadex export puts every body frame at the origin

    def env_step(d):
        return jax.lax.fori_loop(0, n_sub, lambda _, dd: mjx.step(mx, dd), d)

    @jax.jit
    def rollout(batch):
        out, _ = jax.lax.scan(lambda b, _: (jax.vmap(env_step)(b), None), batch, None, length=steps)
        return out

    impl = getattr(d0, "_impl", d0)  # MJX 3.10 moved the contact and constraint arrays here
    result = {
        "model": str(xml_path), "model_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "tier": tier(text), "start": "keyframe 0" if m.nkey else "qpos0",
        "timestep": float(m.opt.timestep), "iterations": int(m.opt.iterations),
        "ls_iterations": int(m.opt.ls_iterations), "integrator": INTEGRATORS[int(m.opt.integrator)],
        "eulerdamp": not (m.opt.disableflags & int(mj.mjtDisableBit.mjDSBL_EULERDAMP)),
        "substeps": n_sub, "control_dt": control_dt, "steps": steps,
        "nbody": int(m.nbody), "nv": int(m.nv), "nu": int(m.nu),
        "mjx_ncon": int(impl.contact.dist.shape[0]), "mjx_nefc": int(impl.efc_J.shape[0]),
        "device": str(jax.devices()[0]), "runs": [],
    }
    for n in envs:
        batch = jax.tree_util.tree_map(lambda x: jnp.broadcast_to(x, (n, *x.shape)), d0)
        t0 = time.perf_counter()
        jax.block_until_ready(rollout(batch))
        compile_s = time.perf_counter() - t0
        t0 = time.perf_counter()
        out = jax.block_until_ready(rollout(batch))
        wall = time.perf_counter() - t0
        z = out.subtree_com[:, root, 2]
        result["runs"].append({
            "envs": n, "compile_and_first_s": round(compile_s, 2), "wall_s": round(wall, 4),
            "env_steps_per_s": round(n * steps / wall),
            "finite": bool(jnp.all(jnp.isfinite(out.qpos))), "upright": bool(jnp.all(z > 0.5 * z0)),
            "root_z_start": round(z0, 4), "root_z_end_mean": round(float(z.mean()), 4)})
        del out, batch
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model", type=Path)
    parser.add_argument("--envs", default="2048,8192")
    parser.add_argument("--steps", type=int, default=100, help="control steps per env")
    parser.add_argument("--control-dt", type=float, default=0.02)
    parser.add_argument("--timestep", type=float)
    parser.add_argument("--iterations", type=int)
    parser.add_argument("--ls-iterations", type=int)
    parser.add_argument("--integrator", choices=INTEGRATORS)
    parser.add_argument("--json", type=Path, help="also write the result here")
    args = parser.parse_args(argv)
    result = bench(args.model, [int(n) for n in args.envs.split(",")], args.steps, args.control_dt,
                   timestep=args.timestep, iterations=args.iterations,
                   ls_iterations=args.ls_iterations, integrator=args.integrator)
    text = json.dumps(result, indent=1)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n")
    print(text)
    return 0 if all(r["finite"] for r in result["runs"]) else 1


if __name__ == "__main__":
    sys.exit(main())
