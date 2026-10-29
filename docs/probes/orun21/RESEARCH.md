# orun21 R1: how practice sets up commands, goals, terrain and budgets

Verified against source: 2026-10-28. Frozen run evidence; read it, never cite
it as current.

R1 reads three bodies of practice (MuJoCo Playground, legged_gym / rsl_rl,
Isaac Lab) and two papers, then sets Cadex against them (§5). It fixes the
design G2 and T1 build on; it changes no code.

## 0. Sources

Every fetched file lives outside the repository, in `~/orun21-research/`
(shallow clones, never committed). Nothing below is copied from them; line
citations are `path:line` at the commit given.

| Short | What | Version | Licence (read from) |
|---|---|---|---|
| PG | MuJoCo Playground, github.com/google-deepmind/mujoco_playground; paths under `mujoco_playground/_src/locomotion/` (`L/`) and `mujoco_playground/config/` (`C/`) | commit `12ad7f3842791ced39f27e5ac96d066bbe361653` (2026-10-21); the Go1 files match the 0.2.0 wheel orun18 used (`~/playground-venv`) up to licence headers | Apache-2.0 (`LICENSE`) |
| PGP | Zakka et al. 2025, "MuJoCo Playground", arXiv 2502.08844 | v1 | — |
| LG | legged_gym, github.com/leggedrobotics/legged_gym; paths under `legged_gym/` | commit `8fa29acc6fd1910c3d9659eef6310bdd301cde0a` (2025-05-29) | BSD-3-Clause (`LICENSE`) |
| RSL | rsl_rl, github.com/leggedrobotics/rsl_rl | commit `11563319134f987f70fb034410496fe3cc7327a9` | BSD-3-Clause (`LICENSE`) |
| IL | Isaac Lab, github.com/isaac-sim/IsaacLab; paths under `source/` | commit `6d377459079a715b4c92df9ea71eff9170f07da4` (2026-10-28) | BSD-3-Clause for these paths (`README.md:120-130`; `isaaclab_mimic` Apache-2.0, Isaac Sim assets proprietary — none read) |
| R21 | Rudin, Hoeller, Reist, Hutter 2021, "Learning to Walk in Minutes Using Massively Parallel Deep RL", CoRL 2021, arXiv 2109.11978 | — | — |
| R22 | Rudin, Hoeller, Bjelonic, Hutter 2022, "Advanced Skills by Learning Locomotion and Local Navigation End-to-End", IROS 2022, arXiv 2209.12827 | — | — |
| CX | Cadex, this checkout (`ouroboros/orun21` at `20f59b17`) | — | LGPL |

## 1. Commands and goals

### 1.1 Velocity commands (all three agree in shape)

| | PG Go1 joystick | LG base | IL velocity env |
|---|---|---|---|
| axes | vx, vy, yaw rate | vx, vy, yaw rate (+ heading) | vx, vy, yaw rate (+ heading) |
| ranges | ±1.5 m/s, ±0.8 m/s, ±1.2 rad/s (`L/go1/joystick.py:88`) | ±1.0, ±1.0, ±1.0; heading ±π (`envs/base/legged_robot_config.py:68-78`) | as LG (`isaaclab_tasks/isaaclab_tasks/core/velocity/velocity_env_cfg.py:137-148`) |
| resample | exponential, mean 5 s, and on reset (`joystick.py:205-208, 289-293`) | every 10 s fixed, and on reset (`envs/base/legged_robot.py:325, 168`) | every 10 s (`velocity_env_cfg.py:137`) |
| stand / zero | per axis on a change: kept with p = 0.9 / 0.25 / 0.5, else 0 (`joystick.py:609-617`) | ‖v_xy‖ ≤ 0.2 → 0 (`legged_robot.py:351`) | 2 % of envs get a zero command (`rel_standing_envs=0.02`) |
| heading | none | on: yaw = clip(0.5·wrap(ψ* − ψ), ±1) (`legged_robot.py:327-330`) | on for 100 % of envs, stiffness 0.5 (`isaaclab/isaaclab/envs/mdp/commands/velocity_command.py:158-192`) |
| curriculum | none in code; PGP B.25 describes flat → wider yaw → rough stages | optional, off: widens vx ±0.5 when tracking > 0.8 (`legged_robot.py:443-452`) | none in the Go1 env |

The command acts only through the observation and the reward in every one.
Heading mode is the go-to-point layer in miniature: a proportional yaw
controller that turns the policy towards a world direction.

### 1.2 Position goals: two routes

**A. A layer over a velocity policy.** Isaac Lab's navigation task
(`isaaclab_tasks/isaaclab_tasks/contrib/navigation/config/anymal_c/navigation_env_cfg.py`)
is exactly this: a 5 Hz high-level policy whose 3-D action (vx, vy, ωz)
overwrites the command observation of a frozen 50 Hz blind velocity policy
(`:49-55, 139-141`; `mdp/pre_trained_policy_action.py:66-105`). The target is
`UniformPose2dCommand` (x, y ±3 m, heading ±π, success 0.5 m;
`isaaclab/isaaclab/envs/mdp/commands/pose_2d_command.py:112-149`), 8 s
episodes, rewards 1 − tanh(d/2) and 1 − tanh(d/0.2) at 0.5 each, |heading
error| at −0.2, termination −400 (`navigation_env_cfg.py:79-94`). The layer can
equally be a hand-written controller (heading mode is one): the low-level
policy never knows.

**B. End to end (R22).** The policy observes the target in the base frame and
the time remaining; the task reward is paid only in the last T_r = 1 s of a
T = 6 s episode, r = (1/T_r)/(1 + ‖x − x*‖²) (Eq. 1). It needs an exploration
bias (cosine of base velocity to the target direction, removed once the task
reward reaches 50 %, Eq. 3) and a stall penalty (−1 below 0.1 m/s while > 0.5 m
away, Eq. 4). Targets 1–5 m, uniform in polar coordinates. 4096 × 48 steps,
2000 iterations, ~1 h. It beats a velocity-tracking baseline at ≥ 95 % success
on every hard terrain (Table I: stairs 0.40 vs 0.22 m, obstacles 0.85 vs
0.35 m, gaps 1.2 vs 0.15 m) and uses less energy at low speed (§III-B). Its
own stated costs (§II-E, §III-C, §IV): less stable training, a seed-sensitive
critic, one preferred walking direction (it does not use its symmetry), and
**no continuous multi-waypoint commands**, which is what G2 asks for.

**For G2 (recommendation for its ADR).** Route A: an omnidirectional
velocity-command policy (vx, vy, yaw rate, Playground's ranges and zeroing)
under a go-to-point layer that turns a point sequence into commands. Reasons,
from the sources: the Go1 velocity policy is already reproduced through Cadex
within 6 % of Playground (orun18 A2, `open-dawn-6825`), so route A reuses a
known-good training recipe; points behind the robot are handled by the
layer's yaw command (heading mode, LG/IL) rather than learnt; arrival
triggers, holds and per-point speeds are layer logic that needs no reward
change; and R22's route has no multi-waypoint form and trains less stably.
Route A's known weakness is R22's own result: on obstacles, gaps and pits the
velocity tracker loses badly, which matters for J1 and partly T2, not G2. That
is E1's comparison.

Two layer forms, both cheap; G2 picks by measurement:
- **scripted layer** (heading mode generalised): yaw rate = k·bearing error,
  speed = the point's commanded speed × a slowdown inside ~0.5 m, zero inside
  the hold radius; side-step (vy) for small lateral errors. No training.
- **trained layer** (IL navigation): a second small policy, more training, but
  learns to cut corners. For later only if the scripted layer fails G2.

The training distribution must then cover what the layer issues: turning on
the spot (vx ≈ 0, |ωz| large), zero commands (holds), and command changes
mid-episode, which Playground's per-axis zeroing and 5 s resampling already
give.

## 2. Terrain and curricula

### 2.1 Generators

**legged_gym** (`utils/terrain.py`, config `legged_robot_config.py:43-66`): a
10 × 20 grid of 8 × 8 m tiles (rows = difficulty levels, columns = types),
0.1 m horizontal and 5 mm vertical scale, 25 m border, built as a trimesh by
default. Types by proportion `[0.1, 0.1, 0.35, 0.25, 0.2]`: smooth slope, rough
slope (+ ±5 cm noise), stairs down, stairs up, discrete obstacles
(`terrain.py:122-137`); stepping stones, gaps and pits with an 8-entry list
(`:138-143`). Difficulty d ∈ [0, 1] scales each (`:115-121`): slope 0.4·d, step
0.05 + 0.18·d m (0.31 m treads), obstacle 0.05 + 0.2·d m, gap 1.0·d m, pit
1.0·d m, on a 3 m flat platform at the tile centre where robots spawn.

**Isaac Lab** (`isaaclab/isaaclab/terrains/config/rough.py:11-53`,
`terrain_generator.py`): the same grid, sub-terrains pyramid stairs 0.2,
inverted stairs 0.2, boxes 0.2, random rough 0.2, slope 0.1, inverted slope
0.1; difficulty = (row + U(0,1))/rows (`terrain_generator.py:235-264`). The Go1
scales boxes to 2.5–10 cm and rough to 1–6 cm
(`isaaclab_tasks/isaaclab_tasks/contrib/velocity/config/go1/rough_env_cfg.py:26-28`).
Targets for navigation come from each tile's `flat_patches`
(`pose_2d_command.py:187-207`).

**Playground**: one static 20 × 20 m Perlin heightfield from a 256 × 256 PNG,
`size="10 10 .05 1.0"` (5 cm relief, ~7.8 cm cells), the same for every env
(`L/go1/xmls/scene_mjx_feetonly_rough_terrain.xml:18-23`; PGP B.25). A stairs
scene and a procedural bowl exist but no task uses them. No curriculum in code.

### 2.2 The curriculum (legged_gym's game rule, kept by Isaac Lab)

Per episode end (`legged_robot.py:421-441`;
`isaaclab_tasks/isaaclab_tasks/core/velocity/mdp/curriculums.py:42-50`): move
**up** a row if the robot got farther than half a tile (4 m) from its origin;
**down** if it covered less than half the distance its command asked for
(‖v*‖ × episode × 0.5); at the top row, go to a random row so the top does
not empty. Initial rows 0–5. R21 §3.1: 1000 iterations to reach the top
levels, 1500 to converge, under 20 min on an A6000. It needs no level-specific
reward: the distance rule rides on the task's own command. For go-to-point the
natural analogue is "reached the points" up, "reached under half" down
(R22 drives its curriculum with success, §II-D).

### 2.3 Heightfields in MJX: how Playground keeps them stable

Playground's rough Go1 trains on a heightfield, but:
1. **Only four sphere feet collide** (r = 23 mm, `go1_mjx_feetonly.xml:11, 62-68`:
   every geom `contype=0 conaffinity=0`, the foot class `conaffinity=1`); the
   floor is `contype=1 conaffinity=0 priority=1`, so the floor's condim 3 and
   friction 1.0 win over the feet's condim 1.
2. Solver `iterations=1 ls_iterations=5`, Euler, `eulerdamp` off, 4 ms step;
   the feet have `solimp="0.9 .95 0.023"`.
3. Shallow relief: 5 cm.
4. **Its default backend is MuJoCo Warp, not MJX-JAX**: `impl="warp"` with
   `naconmax=8*8192`, `njmax=60` for rough (`L/go1/joystick.py:92-94, 107-109`).
   orun18 A1 ran `impl="jax"` (`docs/probes/orun18/a1_train.py:9`), on flat
   only. So Playground's published rough number does not show that MJX-JAX's
   heightfield collider is stable; `~/cadex-train-venv` has no `warp-lang`.

Cadex's failure (`winter-bay-5176`, ADR-714) was a **box block and capsule
arm** on a heightfield under MJX-JAX, with `collision_convex.py:930` overflow
warnings: the convex–heightfield path. The sphere–heightfield pair, the only
one Playground exercises, was never tried in Cadex. That makes a cheap test for
T1 (§5, row T-3): sphere-only feet on the ADR-714 course under MJX-JAX.

### 2.4 Height scans

LG: 17 × 11 points on a 1.6 × 1.0 m grid at 0.1 m, yaw-aligned, observation
clip(z_base − 0.5 − h, ±1) × 5, noise ±0.1 (`legged_robot_config.py:54-55`,
`legged_robot.py:222`); IL the same grid by ray caster, no ×5
(`isaaclab/isaaclab/envs/mdp/observations.py:293-300`). R21's and IL's rough
policies use the scan; **Playground's rough policies are blind** (no ray cast
anywhere in the repository). R22's policy uses the scan for climbing.

## 3. Observations, actions, rewards, budgets, randomisation

### 3.1 Observation and action

| | PG Go1 | LG / IL |
|---|---|---|
| actor | body linvel, gyro, gravity in IMU frame, q − q_home, dq, last action, command: 48, no history (`joystick.py:359-367`) | linvel ×2, angvel ×0.25, projected gravity, command, q − q_default, dq ×0.05, last action (+187 scan): 48/235 (`legged_robot.py:209-222`) |
| noise | uniform: q 0.03, dq 1.5, gyro 0.2, gravity 0.05, linvel 0.1 (`joystick.py:42-51`) | uniform: linvel 0.1, angvel 0.2, gravity 0.05, q 0.01, dq 1.5, scan 0.1 |
| critic | noisy actor obs + clean state, forces, contacts, foot velocities, air time, push force (`:373-388`) | same obs (LG); IL may add privileged |
| action | q* = q_home + 0.5·a, PD Kp 35 Kd 0.5 (`:39, 253`; `base.py:59-61`) | q* = q_default + scale·a; scale 0.5 base, 0.25 Go1/A1 |
| rates | 4 ms sim, 20 ms control; 20 s episodes | 5 ms × 4 = 20 ms; 20 s episodes |

### 3.2 Rewards and terminations

Playground's Go1 (`joystick.py:52-79`, summed ×dt, clipped ≥ 0, `:278`):
lin-vel tracking 1.0 and yaw 0.5 as exp(−err²/0.25); lin_vel_z −0.5;
ang_vel_xy −0.05; orientation −5; joint limits −1; pose +0.5; termination −1;
stand_still −1 (‖cmd‖ < 0.01); torques −2e-4; action rate −0.01; energy −1e-3;
feet clearance −2, feet height −0.2, feet slip −0.1, air time +0.1. LG base
(`legged_robot_config.py:131-154`): the same tracking pair, lin_vel_z −2,
torques −1e-5, dof_acc −2.5e-7, air time +1.0, collision −1, action rate
−0.01, only positive totals. Terminations: Playground only when upside down
(`joystick.py:307-309`); LG/IL on base contact; all three bootstrap time-outs.

### 3.3 Domain randomisation

| | PG Go1 (`L/go1/randomize.py:27-73`) | LG | IL |
|---|---|---|---|
| friction | floor U(0.4, 1.0) | U(0.5, 1.25) | fixed 0.8/0.6 |
| mass | all ×U(0.9, 1.1), trunk +U(−1, 1) kg | base ±1 kg (off) | base ×[0.8, 1.25] |
| CoM | trunk ±5 cm | — | ±5 cm xy |
| joints | qpos0 ±0.05 rad, frictionloss ×U(0.9,1.1), armature ×U(1,1.05) | — | — |
| reset | xy ±0.5 m, yaw ±π, base vel ±0.5 (`joystick.py:154-168`) | xy ±1 m, vel ±0.5 | xy ±0.5 m, any yaw |
| pushes | off by default | every 15 s, ±1 m/s | every 10–15 s, ±0.5 m/s |

### 3.4 Budgets

| | envs | steps/iter/env | iterations | env steps | wall |
|---|---|---|---|---|---|
| PG Go1 flat | 8192 | 20 (× 32 mb × 4 upd) | — | 200 M (`C/locomotion_params.py:30-63`) | 417 k steps/s on A100 → ~8 min (PGP Tab. VII); < 5 min on 2 × 4090 (PGP §IV-B1); 385 s on our 5090 (orun18 A1) |
| PG Go1 rough | 8192 | 20 | — | 200 M | 291 k steps/s → ~11.5 min (PGP Tab. VII) |
| LG/IL flat | 4096 | 24 | 300 | ~30 M | < 4 min (R21 §4) |
| LG/IL rough | 4096 | 24 | 1500 | ~150 M | < 20 min (R21 §4) |
| R22 position | 4096 | 48 | 2000 | ~390 M | ~1 h |
| IL navigation (high level) | — | 8 | 1500 | — | — |

PPO: Playground lr 3e-4 fixed, γ 0.97, entropy 0.01, 4 updates × 32
minibatches, 512-256-128 nets; rsl_rl lr 1e-3 **adaptive on KL** (target 0.01,
÷1.5 above 0.02, ×1.5 below 0.005; `rsl_rl/algorithms/ppo.py:253-256`),
γ 0.99, λ 0.95, 5 epochs × 4 minibatches, clip 0.2. R21 §4.2: learning
degrades below ~25 steps per env per iteration; 100–200 k samples per batch is
the best trade-off.

## 4. What this means for G2 and T1, in one paragraph each

**G2.** Train a Playground-shaped omnidirectional velocity policy (vx, vy,
yaw rate; exponential 5 s resampling with per-axis zeroing; yaw reset ±π) on
the Go1 at Playground's 200 M steps, then drive it with a scripted go-to-point
layer whose sequence generator is one seeded source shared by training (as a
command source, optionally) and the judge. A point behind is a turn on the
spot; a hold is a zero command.

**T1.** One generator in legged_gym/Isaac Lab's form: a grid of tiles, rows
= levels and columns = kinds, each kind a function of d ∈ [0, 1], spawning on
a central platform, plus the game-inspired row curriculum. Cadex's box course
(ADR-716/717/744/745) already compiles steps, slopes, bumps, platforms and rocks
from one spec into placed boxes; what it lacks is levels, a curriculum,
non-x layouts, walls/mazes and a mesh/heightfield course. Heightfields: test
the sphere-feet pair first (T-3) before choosing between MJX-JAX, MuJoCo Warp
(a new dependency) or boxes only.

## 5. Where Cadex differs

CX citations are to this checkout. "keep / change / test" is the decision;
the criterion is where it is acted on.

| # | Topic | Practice | Cadex today | Decision | Criterion |
|---|---|---|---|---|---|
| C-1 | lateral command | vx, vy, yaw rate everywhere | goal kinds `speed` (forward only) and `yaw_rate`; no vy kind (`src/Mod/cadex/cadex_assembly_api.py:4380-4515`) | **change**: add a lateral speed goal (or the layer side-steps by turning only — measure) | G2 |
| C-2 | heading / point following | heading mode (LG, IL); pose command (IL nav) | waypoint goal advances on a clock, not on arrival, no hold, no speed per point, no marker (`training/cadex_train.py:2452-2464`, ADR-751) | **change**: arrival-triggered sequence with holds and per-point speed, one seeded generator for train and judge | G1, G2 |
| C-3 | command resampling | exp(5 s) per env (PG); 10 s fixed (LG/IL) | fixed `resample_seconds` or held all episode; host-drawn pool of 4096 episodes (`cadex_train.py:2318-2325, 2546`) | **test**: is the 4096-episode pool diverse enough for a layer's command stream? keep fixed segments if G2 passes | G2 |
| C-4 | standing | per-axis zeroing (PG), 2 % (IL), ‖v‖ ≤ 0.2 → 0 (LG) | expressed as a zero band (ADR-824) | **keep**: bands express the same distribution; G2's task states the zero fraction | G2 |
| C-5 | position end to end | R22 | not built | **keep for later**: E1 | E1 |
| C-6 | actor obs: gravity, body linvel | standard | not declarable in the script; A2/T1 injected raw MJCF sensor rows (`docs/probes/orun18/a2.md`) | **change**: declarable kinds, so the biped and leon V need no bespoke bundle | G3, K1 |
| C-7 | observation noise | uniform on every channel | Gaussian on tracker/load only (`cadex_train.py:2218, 3626-3637`) | **test**: the Go1 at 0/30 falls without it (A2); add only if G2's judge shows it matters on held-out seeds | G2 |
| C-8 | last action | in the actor | `_rate` channels (ADR-696), in the actor when `role=policy` | **keep** | — |
| C-9 | history | none (PG, LG) | none | **keep** | — |
| C-10 | action parameterisation | q_home + 0.5·a | full joint/torque box `tanh(a)·half + mid` (`cadex_train.py:2985-2988`) | **change**: home-relative scale as a task option; the Go1 A2 path already does it by hand | G3, K1 |
| C-11 | reward scale | ×dt, clipped ≥ 0 | no ×dt, floor off by default (`cadex_train.py:5012-5056`); A2 passes `--reward-floor 0` and ×dt weights | **change**: make Playground's form the documented default | K1 |
| C-12 | terminations | upside-down (PG); base contact (LG/IL) | authored per task; leon tasks ended at 32° tilt (MUJOCO-GAP) | **keep** the mechanism; RECIPE states upside-down as the default | K1 |
| C-13 | yaw and xy reset | yaw ±π, xy ±0.5 m | `reset_variation` has no yaw or xy (`cadex_assembly_api.py:4074`) | **change**: points behind the robot need a yaw-uniform start | G2 |
| C-14 | DR draw | once per env for the run (PG's vmapped per-env model; LG at env creation) | once per env for the run (`cadex_train.py:2266`) | **keep**: the same as PG and LG | — |
| C-15 | DR coverage | CoM ±5 cm, qpos0 ±0.05 rad | mass/inertia, damping, armature, frictionloss; no CoM or qpos0 | **test** on the Go1's held-out judge | G2 |
| C-16 | pushes | off (PG), every 10–15 s (LG/IL) | `disturbance` force blocks (`cadex_train.py:3407`) | **keep** | — |
| C-17 | PPO lr | 3e-4 fixed (PG); 1e-3 KL-adaptive (rsl_rl) | 3e-4 fixed, Playground's | **keep**: within 6 % of PG on the Go1 | — |
| C-18 | env count default | 8192 (PG), 4096 (LG/IL) | `--envs 256` (`cadex_train.py:4980`) | **change**: the default should be a usable run, not a smoke test | S1 |
| C-19 | budget | 200 M steps (PG); 30 M flat / 150 M rough (LG) | 200–300 iterations default (RECIPE §4); 256 × 20 × 200 = 1 M steps | **change**: state budgets in env steps; Go1 G2 at PG's 200 M | G2, S1 |
| C-20 | sim model | feet-only spheres, solver 1/5, 4 ms Euler | engine MJCF solver 100/50, 2 ms, no solver knob (`src/Mod/cadex/CadexDynamics.py:7486`); leon V's training model fixes it outside Cadex | **change**: P1 ports the training model | P1 |
| C-21 | terrain layout | tile grid, levels × kinds | box course along x; random pool of 32 courses (ADR-717) | **change**: grid of tiles, levels, non-x layouts | T1 |
| C-22 | curriculum | game rule on distance | none; manual warm-start task changes (`cadex_train.py:410-451`) | **change**: game rule on points reached | T1, T2 |
| C-23 | heightfield in MJX | Playground: sphere feet only, Warp backend | ADR-714 heightfield diverges under MJX-JAX (box/capsule rig); boxes used instead | **test**: sphere-only feet on the ADR-714 course under MJX-JAX, then decide hfield vs boxes vs Warp. Done, ADR-854: sphere and capsule contacts are stable and the Go1 trains on a heightfield to its flat result; box and mesh on a heightfield are refused; no Warp | T1 |
| C-24 | height scan | 187 points, 1.6 × 1.0 m (LG/IL); blind (PG) | 15 points −0.1…+0.3 m (+45 far, ADR-821), noise-free | **test**: blind first on T1's levels (PG shows blind works on 5 cm); widen only when steps or boxes fail | T2 |
| C-25 | walls / maze | IL navigation: obstacles by terrain tiles | none | **change**: wall and corridor kinds | T1, T2 |
| C-26 | judge | success = within 0.5 m (IL nav, R22) | waypoint reached within 300 mm (`waypoints_reached`) | **keep**: G2's own thresholds (0.3 m reach, 0.15 m hold) are stricter | G2 |
