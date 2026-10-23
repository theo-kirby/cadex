# orun18 sources: third-party software and data, and their licences

Verified against source: 2026-10-23. Everything listed here lives outside the
repository. The repository holds only our own code that imports or reads it
(`a1_train.py`, `go1_judge.py`), and no line copied from any of them.

| What | Where (outside the repo) | Version / commit | Licence (read from) | Used for |
|---|---|---|---|---|
| MuJoCo Playground (`playground` on PyPI, github.com/google-deepmind/mujoco_playground) | `~/playground-venv` | 0.2.0 | Apache-2.0 (wheel `licenses/LICENSE`, classifier) | A1: `Go1JoystickFlatTerrain`, `brax_ppo_config`, its Go1 domain randomiser |
| Brax | `~/playground-venv` | 0.14.2 | Apache-2.0 (wheel METADATA) | A1's PPO (same version as `~/cadex-train-venv`) |
| JAX / jaxlib, CUDA 12 plugin | `~/playground-venv` | 0.7.2 | Apache-2.0 | A1 (same version as `~/cadex-train-venv`) |
| MuJoCo, MuJoCo MJX | `~/playground-venv` | 3.10.0 / 3.10.0 | Apache-2.0 (wheel METADATA `License-Expression`) | A1's physics (MJX) and D3's referee (MuJoCo, CPU) |
| warp-lang | `~/playground-venv` | 1.18.0 | pulled in by `playground`'s requirements; not used (A1 runs `impl="jax"`) | — |
| MuJoCo Menagerie (github.com/deepmind/mujoco_menagerie) | `~/menagerie/mujoco_menagerie`, symlinked into Playground's `external_deps/` | `1b86ece576591213e2b666ebf59508454200ca97` (the commit Playground 0.2.0 pins, `MENAGERIE_COMMIT_SHA`) | per model; `unitree_go1/`: BSD-3-Clause, © 2016-2022 Unitree Robotics (`unitree_go1/LICENSE`, `README.md`) | Go1 meshes and base MJCF behind Playground's `go1_mjx_feetonly.xml` |

Installed with `uv venv --python 3.12 ~/playground-venv` and
`uv pip install playground==0.2.0 "jax[cuda12]==0.7.2" brax==0.14.2
mujoco==3.10.0 mujoco-mjx==3.10.0`: the jax, brax and MuJoCo pins match
`~/cadex-train-venv`, so A's comparison does not also compare library
versions.

Motion capture for C1 is not yet searched; its entries come here before any
download is used.
