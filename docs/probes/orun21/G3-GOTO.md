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
- **A relay defect, found, then fixed (ADR-863).** `cadex_relay.py` kept the export's
  episode (`solver_step_s` 0.002 × 10) on a concept whose model steps at 0.0025 s. The
  trainer never sets the timestep, so every relayed concept run before ADR-863 took 25 ms
  control steps (40 Hz) while the task said 20 ms. The relay now sets the substeps from the
  model's step (8 here). `cadex_joystick.py` already did, so the G3 runs above were at 50 Hz.
- **What binds: the slow walk.** This is the Go1's `kind-ridge-3238` signature, stronger:
  the Go1's walk min was 0.873, leon V's is 0.80. A hypothesis for the next unit: the torque
  and energy terms are in absolute N·m, and leon V weighs 2.6× the Go1 (33.3 against
  12.7 kg). The same weights then charge its slow gait more against a tracking kernel
  (`exp(-err²/0.25)`) that pays 0.96 for a 0.1 m/s miss. Mass-normalised effort terms, or
  `--goto-share 0` (the Go1's run1 walk min was 0.924), should lift the walk legs. Nothing
  here tests that yet.

## The share-0 hypothesis, refuted (ADR-863)

The hypothesis: the go-to-point layer's share is what costs the slow walk (the Go1's walk
minimum was 0.924 at share 0 and 0.873 at share 0.2, `kind-ridge-3238`), so training with no
layer should lift leon V's walk legs above 0.85. `runs/s0` is `runs/g2`'s command without
`--goto`: 1260 iterations, 206.4 M steps, `wall_time_s` 663.9, best reward/step 0.0254 at
iteration 1154. It was judged by the same `g2_judge.py` on the same held-out seeds 0–9.

| policy | pass | reach | hold | speed | falls | ratio min / max | worst seed min | total s |
|---|---|---|---|---|---|---|---|---|
| s0 it 900 | 0/10 | 10 | 10 | 0 | 0 | 0.799 / 0.937 | 0.799 | 950.9 |
| s0 best (1154) | 0/10 | 10 | 10 | 0 | 0 | 0.744 / 0.943 | 0.744 | 966.7 |
| s0 final (1259) | 0/10 | 10 | 10 | 0 | 0 | 0.792 / 0.936 | 0.792 | 948.1 |

Every seed has a leg at 0.79–0.84, and the best leg is 0.94, below the 0.96–0.98 run legs
of share 0.2. Removing the layer made leon V's tracking worse overall, not better. The share
is not what binds on this robot. What is left of the hypotheses in this file is the effort
scale: Playground's torque and energy weights in absolute N·m on a robot 2.6× the Go1's
mass, against a tracking kernel that pays 0.96 for a 0.1 m/s miss. That test is not run.
Per the owner's live edit (2026-10-29), G3 on leon V stops here at 4/10 (`runs/g2` it 900),
and the next unit is K1's rewrite of RECIPE.md.

## The biped, by RECIPE.md alone (ADR-865)

The orun9 biped (0.646 kg, six position servos, legs of roll, pitch and knee: no hip yaw) taken
from its CAD by `training/RECIPE.md` alone, in `orun21-lab/g3/biped`. The CAD existed and no
geometry was in question, so per §R the concept was skipped and the route began at the export.

| step | command | result |
|---|---|---|
| cut (§R.6) | `cadex_training_model.py cut --project orun9-biped --out cut.xml` | 0.97 s; implicitfast, 2/3 iterations |
| export (§R.4) | `cadex export --project orun9-biped --out export` | 6.6 s; `model-model.xml` 2b9c8268, the cut's source |
| relay (§R.7) | `cadex_relay.py export/b1_walk-task.json cut.xml --out relay` | 28 sensors kept; the battery's mass entry dropped |
| task (§G.2) | `cadex_joystick.py relay/outputs/b1_walk-task.json --out . --label biped_cut --speeds 0.24,0.128,0.192` | first refused (`KeyError: goal_algorithm`: the biped's task has no goal) |
| train (§G.3) | G2's command with `--goto walk:0.064-0.112,run:0.16-0.24 --goto-share 0.2`, `--cad-model export/model-model.xml` | below |
| judge (§G.4) | `g2_judge.py POLICY TASK OUT --bands walk:0.064-0.112,run:0.16-0.24` | below |

The speeds are the Go1's scaled by 0.16, the biped's `W3-speed` top (240 mm/s) over 1.5 m/s.

**What the recipe got wrong, in the order the biped found it.** Each fix leaves the Go1 and
leon V as they were: leon V's re-written task is byte-identical, and the Go1's has the same
reward expressions, payload and reset.

1. *A source with no goal.* The writer read `goal_algorithm` from the source bundle. The fix
   writes a stated one when the source has none.
2. *A negative payload.* ±1 kg on a 0.26 kg pelvis scales its mass by −2.85 to 4.85. Now it is
   capped at ±20% of the trunk's mass (the Go1's 5.2 kg and leon V's chest keep 1 kg).
3. *The policy stood still* (`runs/s300`, 300 iterations, 181.5 s). At every command from 0 to
   0.2 m/s and 0.19 rad/s its mean speed was 0.000. Playground's tracking width, 0.25 (m/s)²,
   pays `exp(-0.2²/0.25)` = 0.85 for standing at the biped's run speed, and episodes averaged 334
   of 1000 steps because the 0.5 m/s reset kick tipped it over. The widths now scale with the
   square of the speed ratio (0.0064 here) and the kick with the ratio (0.08 m/s, 0.08 rad/s).
   `runs/s300b` (185.5 s) then ran every episode to 1000 steps and walked: at iteration 200,
   0.064 / 0.137 / 0.203 m/s at 0.08 / 0.16 / 0.24, and 0.095 m/s sideways at 0.1. It did not
   turn in place (0.000 rad/s at ±0.19), and reached 0–1 of 8 points per held-out seed.
4. *Too short a budget for a turn without a yaw joint.* `runs/g2`, G2's full budget (1260
   iterations, 206.4 M steps, `wall_time_s` 478.6), learned a stepping turn: −0.177 / +0.176
   rad/s at ∓0.192 at iteration 1200.
5. *The judge's time bound.* Every seed of iteration 1200 ran to its bound of each leg at its
   full speed plus 10 s (4,238.7 s over ten seeds), and 1–6 of 8 points were reached. The bound
   is now each leg and a half turn at half their speed. Play stops a second after the last point,
   so a sequence that finishes is judged as before. With it, 6/10 seeds reached all 8 points.
6. *The layer chattered at its 60° edge.* On seed 9 the first point lies 65° off. The robot turned
   it inside 60°, the layer switched to a diagonal walk with `vy` at its −0.128 limit, and the
   step-off yawed it back out at up to +0.7 rad/s: 0.9 m made in 40 s, and 226 s to the first
   point. A turn on the spot now goes on until the point is within 30° (`face_deg`;
   `training/test_cadex_goto.py` holds it and fails without the fix). A pace floor tried first
   (`approach_min` capped at a sixth of the forward limit, on the hypothesis that the biped
   circled points) moved nothing (5/10 seeds reached all points against 6/10) and was taken
   out again.
7. *Judging on the export.* `cadex_goto play` refused a policy whose training model was not the
   bundle's. `--other-model` (and `g2_judge.py --other-model`) plays it by channel name and
   records both digests.

**Judged.** `runs/g2`, held-out seeds 0–9, the biped's bands, the 30° exit and the new bound:

| checkpoint | model | pass | reach | hold | speed | falls | slowest leg per seed, min–max | total s |
|---|---|---|---|---|---|---|---|---|
| 900 | cut | 0/10 | 0 | 10 | 4 | 9 | 0.636–0.760 | 1,730.3 |
| **1200** | cut | **0/10** | 10 | 10 | 0 | 0 | 0.801–0.849 | 4,016.5 |
| best (1236) | cut | 0/10 | 10 | 10 | 0 | 0 | 0.717–0.770 | 3,911.0 |
| final (1259) | cut | 0/10 | 0 | 10 | 3 | 0 | 0.734–0.897 | 8,282.4 |
| **1200** | **export** | **2/10** | 10 | 10 | 2 | 0 | 0.801–0.858 | 3,940.0 |

At iteration 1200 on the export, all 80 points were reached within 0.255 m, every hold stayed within
0.100 m and nothing fell. Every seed's slowest straight leg ran at 0.80–0.86 of its command
(range over all legs 0.801–0.939), so eight seeds fail on speed alone. It is the slow-walk miss
of leon V and the Go1 (`kind-ridge-3238`), on a robot a twentieth of the Go1's mass, so the
effort-scale hypothesis above cannot be the whole of it. The final checkpoint had come apart
(reach 0/10), as leon V's did, so the checkpoint has to be chosen by judging (§B.5).

**The 30° exit, re-judged on the others.** The Go1's `g2-goto-s20` passes 10/10 as before
(913.2 s against 884.1 s; reach ≤ 0.255 m, hold ≤ 0.100 m, ratios 0.870–0.986 against
0.873–0.987). leon V's iteration 900 passes 3/10 against 4/10, failing on speed alone
(0.801–0.982), reach and holds unchanged.

**Not done.** The biped's concept (`examples/concept/orun9-biped.json`) has not trained on §G.
The writer's 0.1 m swing height and the sequences' 2–5 m spacing are still the Go1's. On the biped
a leg takes 30–60 s.
