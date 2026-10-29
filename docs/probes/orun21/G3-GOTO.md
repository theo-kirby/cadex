# G3: go-to-point on leon V's concept, with G2's task, recipe and judge

Verified against source: 2026-10-29 (this commit). Frozen run evidence; read it, never cite
it as current.

G3's first robot after the Go1 (ADR-862). Only the robot changed. The task is G2's, written
onto leon V's model by `training/cadex_joystick.py`. The trainer command is the Go1's G2
command (`G2-GOTO.md`, `g2-goto-s20`). The judge is `g2_judge.py` with the same bands,
the same held-out seeds 0–9 and the same bar.

## The model and the task

- **Model.** leon V's frozen spec, with the chest raised to the CAD's 33.31 kg
  (`orun21-lab/s1-iter/concept`, ITERATION.md §9), and the export's trot task re-laid onto
  it (`cadex_relay.py`). It has 14 position drives, four sphere paws and a 2.5 ms Euler
  step.
- **Task.** `cadex_joystick.py s1-iter/concept/relay/outputs/trot-task.json --out
  orun21-lab/g3/leonv-concept` (0.6 s). The writer found the root `c_chest_frame` and the
  four paws. It kept 50 Hz control at 8 substeps, from the model's own step. It wrote 68
  actor channels, 13 reward terms (`dof_pos_limits` split in two to fit the formula bound)
  and 52 randomisation entries. Speeds are the Go1's: ±1.5, ±0.8 m/s and ±1.2 rad/s.
- **The writer against the Go1.** On `go1/outputs/go1_joystick-task.json` it writes
  orun18's bundle back again: every reward expression, randomisation entry (in a2's order),
  reset, termination, action bound, episode and goal. Only the channel names differ
  (`q_FR_hip_joint` for `qFRh`).

## Runs

Each run is G2's command on this bundle, seed 1, cold, under the 30G scope, one at a time on
the 5090.

| run | iterations | env steps | trainer `wall_time_s` | reward/step at end |
|---|---|---|---|---|
| Go1 g2-goto-s20 (G2) | 1260 | 206.4 M | 332.9 | |
| leon V `runs/s300` (screen) | 300 | 49.2 M | 226.5 | 0.0215 |
| leon V `runs/g2` | 1260 | 206.4 M | 601.9 | 0.0248 (best 0.0252 at 1113) |

## Ten held-out sequences (`g2_judge.py`, bands `walk:0.4-0.7,run:1.0-1.5`)

| policy | pass | reach | hold | speed | falls | walk ratio min / mean | run ratio min | total s |
|---|---|---|---|---|---|---|---|---|
| s300 final | 0/10 | 2 | 10 | 0 | 0 | 0.0 (stalls) | | 1,003.4 |
| g2 it 900 | **4/10** | 10 | 10 | 4 | 0 | 0.800 / 0.894 | 0.963 | 915.9 |
| g2 best (1113) | 2/10 | 10 | 10 | 2 | 0 | 0.798 | | 915.8 |
| g2 final (1259) | 2/10 | 10 | 10 | 2 | 0 | 0.788 | | 970.6 |

At iteration 900 all 80 points were reached within 0.253 m and every hold stayed within
0.100 m. Every one of the 8 legs below the bar is a walk leg, run at 0.40–0.45 m/s
against a command of about 0.5 m/s. Run legs track 0.963–0.98.

Constant commands, final policy, mean of seconds 4–8 (`orun21-lab/g3/tools/steady.py`):
0.5 → 0.433, 1.0 → 0.976, 1.5 → 1.448 m/s forward; 0.5 → 0.44 m/s lateral; 1.0 → 0.99 rad/s
yaw. The screen's policy stood still at 1.5 m/s.

## What had to change, and what is a defect

- **Nothing robot-specific beyond the bundle.** The writer reads the root, drives, ranges,
  keyframe, feet and floor from the model. Speed bands and speeds were left at the Go1's.
- **A judge defect, fixed.** `cadex_goto play` read a fall from the root's *frame* height.
  leon V's concept chest frame sits at the floor (z = 0; its geoms are offset up), so home
  height was 0 and a 1 mm dip read as a fall. The first judging of the screen gave 7
  "falls", 3 of them inside 1.4 s. It now reads the base's centre of mass. On the Go1,
  `g2-goto-s20` re-judges 10/10, 884.14 s, ratios 0.873–0.987, as G2-GOTO.md had it.
- **A relay defect, found and not fixed.** `cadex_relay.py` keeps the export's episode
  (`solver_step_s` 0.002 × 10) on a concept whose model steps at 0.0025 s. The trainer
  never sets the timestep, so every relayed concept run so far took 25 ms control steps
  (40 Hz) while the task says 20 ms. `cadex_joystick.py` sets the substeps from the model.
- **What binds: the slow walk.** This is the Go1's `kind-ridge-3238` signature, stronger:
  the Go1's walk min was 0.873, leon V's is 0.80. A hypothesis for the next unit: the torque
  and energy terms are in absolute N·m, and leon V weighs 2.6× the Go1 (33.3 against
  12.7 kg). The same weights then charge its slow gait more against a tracking kernel
  (`exp(-err²/0.25)`) that pays 0.96 for a 0.1 m/s miss. Mass-normalised effort terms, or
  `--goto-share 0` (the Go1's run1 walk min was 0.924), should lift the walk legs. Nothing
  here tests that yet.
