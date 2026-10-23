# orun18 sources: third-party software and data, and their licences

Verified against source: 2026-10-23. Everything listed here lives outside the
repository. The repository holds only our own code that imports or reads it
(`a1_train.py`, `a2_bundle.py`, `go1_judge.py`, and for C2 `retarget.py`,
`clip_carry.py`, `retarget_sheet.py`), and no line copied from any of them.

| What | Where (outside the repo) | Version / commit | Licence (read from) | Used for |
|---|---|---|---|---|
| MuJoCo Playground (`playground` on PyPI, github.com/google-deepmind/mujoco_playground) | `~/playground-venv` | 0.2.0 | Apache-2.0 (wheel `licenses/LICENSE`, classifier) | A1: `Go1JoystickFlatTerrain`, `brax_ppo_config`, its Go1 domain randomiser |
| Brax | `~/playground-venv` | 0.14.2 | Apache-2.0 (wheel METADATA) | A1's PPO (same version as `~/cadex-train-venv`) |
| JAX / jaxlib, CUDA 12 plugin | `~/playground-venv` | 0.7.2 | Apache-2.0 | A1 (same version as `~/cadex-train-venv`) |
| MuJoCo, MuJoCo MJX | `~/playground-venv` | 3.10.0 / 3.10.0 | Apache-2.0 (wheel METADATA `License-Expression`) | A1's physics (MJX) and D3's referee (MuJoCo, CPU) |
| warp-lang | `~/playground-venv` | 1.18.0 | pulled in by `playground`'s requirements; not used (A1 runs `impl="jax"`) | — |
| MuJoCo Menagerie (github.com/deepmind/mujoco_menagerie) | `~/menagerie/mujoco_menagerie`, symlinked into Playground's `external_deps/` | `1b86ece576591213e2b666ebf59508454200ca97` (the commit Playground 0.2.0 pins, `MENAGERIE_COMMIT_SHA`) | per model; `unitree_go1/`: BSD-3-Clause, © 2016-2022 Unitree Robotics (`unitree_go1/LICENSE`, `README.md`) | Go1 meshes and base MJCF behind Playground's `go1_mjx_feetonly.xml`; A2's bundle model, written by `a2_bundle.py` to `~/orun18/a2/outputs/` and never committed |

Installed with `uv venv --python 3.12 ~/playground-venv` and
`uv pip install playground==0.2.0 "jax[cuda12]==0.7.2" brax==0.14.2
mujoco==3.10.0 mujoco-mjx==3.10.0`: the jax, brax and MuJoCo pins match
`~/cadex-train-venv`, so A's comparison does not also compare library
versions.

## C1: the motion capture (licence read 2026-10-23, before any download)

Both of the charter's candidates are **one capture**. Peng et al. 2020's
`motion_imitation` retargets the AI4Animation dog (Zhang, Starke et al. 2018,
mode-adaptive networks): its `retarget_motion/data/dog_clips_info.txt` maps
each clip to the capture's take names (`D1_010_KAN01_001` → `dog_run00`), and
its `retarget_motion/data/LICENSE.txt` (239 bytes) reads, whole:

> The motion capture data is available only under the terms of the
> Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) license.
> https://creativecommons.org/licenses/by-nc/4.0/legalcode
> https://github.com/sebastianstarke/AI4Animation

AI4Animation's README ("Copyright Information") says the same of its motion
capture data, and of the project's code: "only for research or education
purposes, and not freely available for commercial use or redistribution".
The repository's own `LICENSE.txt` (Apache-2.0) covers its code, not this
data.

| What | Where (outside the repo) | Version | Licence | Used for |
|---|---|---|---|---|
| AI4Animation dog capture, SIGGRAPH 2018 (`starke-consult.de/AI4Animation/SIGGRAPH_2018/MotionCapture.zip`, linked from github.com/sebastianstarke/AI4Animation) | `~/mocap/ai4animation/` | 33,422,409 bytes, Last-Modified 2018-06-02; sha256 in `~/mocap/SHA256SUMS` | CC BY-NC 4.0 | C2: the raw takes (skeleton with spine), if the keypoint clips below are too coarse |
| `motion_imitation` retargeted dog clips (github.com/google-research/motion_imitation, `retarget_motion/data/`) | `~/mocap/motion_imitation/` | commit `d0e7b963c5a301984352d25a3ee0820266fa4218` | CC BY-NC 4.0 (the data's own `LICENSE.txt`); the repo's code is Apache-2.0 and none of it is copied | C2: `dog_run00`–`dog_run04` (the capture's `D1_010`/`D1_031` runs: canter or gallop, read in C2), `dog_trot`, `dog_pace`, `dog_walk00` |

`motion_imitation/data/motions/` (the DeepMimic-format clips its policies
train on) holds pace, trot, spin and backwards clips only: no canter or
gallop, so it is not the C1 source.

**Why this counts as usable, and on what terms.** CC BY-NC 4.0 is a clear
licence: it permits copying and adapting the data for purposes "not
primarily intended for or directed towards commercial advantage or monetary
compensation", with attribution. orun18's C is a research diagnosis (does
animal motion give leo its style?), which is that purpose. The terms the run
keeps:

- **Attribution:** this file, and the R1 report, credit Zhang, Starke,
  Komura and Saito, "Mode-Adaptive Neural Networks for Quadruped Motion
  Control", SIGGRAPH 2018, and the AI4Animation project; and Peng et al.
  2020 for the retargeted keypoints if those are what C2 reads.
- **Nothing NC enters the product.** The data, the retargeted clip (an
  adaptation, so also BY-NC) and any policy trained on it stay outside the
  repository and out of every release payload. The repository gets only our
  own retargeting code and the outputs' sha256.
- **Owner's call, not the run's:** whether a leo policy trained on this
  clip may later be used in anything commercial. Under BY-NC the run assumes
  not; a commercial use would need a licence from the capture's authors or a
  different capture.

**Fetched 2026-10-23**, after the licence above was read: 16 files under
`~/mocap/motion_imitation/` and `MotionCapture.zip` (51 BVH takes, no
licence file inside) under `~/mocap/ai4animation/`; `~/mocap/SHA256SUMS`
holds all 17 hashes. A first read of the keypoint clips (`*_pose.txt`, 87
columns, root position first, y up; 60 frames/s assumed from
`dog_clips_info.txt`'s trims, e.g. 6.65 s = frame 397): the root's
horizontal speed is 4.07 m/s median on `dog_run01` (155 frames) and 3.13 on
`dog_run02` (203), against 1.07 on `dog_walk00`, with the root 0.41–0.53 m
up. That is canter-to-gallop speed for a dog this size. The footfall order is
C2's to read; units and frame rate are assumptions until C2 checks them
against the BVH.

**C2 checked them (2026-10-23, `c2-retarget.md`).** C2 reads the BVH takes,
not the keypoint text: they are in cm, y up, at 60 fps (`Frame Time:
0.0166667`), on a 27-joint skeleton with a two-body spine. Four takes are
extracted from `MotionCapture.zip` to `~/mocap/ai4animation/extract/`:
`D1_010_KAN01_002` (`dog_run01`, rotary gallop 3.6–4.4 m/s),
`D1_010_KAN01_003` (`dog_run02`, rotary gallop 2.7–3.4 m/s), `D1_031_KAN01_001`
(trot 2.1–2.3 m/s) and `D1_055_KAN01_001` (pace 0.8–1.1 m/s). `retarget.py`
writes the four retargeted strides to `~/mocap/retargeted/` (an adaptation,
so also CC BY-NC 4.0, and never committed). Their sha256 are in
`c2-retarget.md`. The repository holds only `retarget.py`, `clip_carry.py`,
`retarget_sheet.py` (our code) and the stills `c2-retarget.png`. The stills
are a drawing of the capture and of its adaptation, so they carry the
capture's terms: CC BY-NC 4.0, credited as above. They sit only in
`docs/probes/`, which no payload carries.

No cat capture with a licence of this standing was found in this pass; the
dog is the source, as D5 allows.
