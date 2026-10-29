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

## Step back on the slow walk (`kind-ridge-3238`)

Three attempts (share 0, the 30° exit, the biped) left the slow walk where it was, so this
section reads it step by step before any lever is chosen (`g3_slowwalk.py`; it plays
`cadex_goto play` unchanged and logs, each control step, what the judge reads beside the
layer's vx, vy, wz and the base's measured body-frame velocity).

**The denominator is the command.** The biped's seed 4 on the export (iteration 1200), every
straight walk leg the judge read:

| point | band speed | layer vx | layer vy | measured forward | ratio | deficit m/s |
|---|---|---|---|---|---|---|
| 1 | 0.068 | 0.0680 | −0.0022 | 0.0560 | 0.823 | 0.0120 |
| 2 | 0.099 | 0.0990 | −0.0014 | 0.0875 | 0.884 | 0.0115 |
| 3 | 0.111 | 0.1109 | −0.0025 | 0.0997 | 0.898 | 0.0114 |
| 4 | 0.101 | 0.1010 | −0.0018 | 0.0893 | 0.884 | 0.0117 |
| 5 | 0.068 | 0.0680 | −0.0020 | 0.0558 | 0.821 | 0.0122 |
| 6 | 0.065 | 0.0650 | −0.0021 | 0.0526 | 0.810 | 0.0124 |
| 7 | 0.081 | 0.0810 | −0.0023 | 0.0689 | 0.850 | 0.0121 |

The layer commands the band speed itself: `pace = min(speed, max(distance, approach_min))`
and `approach_min` (0.25 m/s) is above every biped speed, so there is no approach slow-down,
and the judge keeps only steps whose commanded speed equals the point's. The mean bearing
is −0.8° to −1.9°, so `cos(bearing)` costs under 0.1%. The critic's suspicion (the ratio
divides by the band while the layer commands less) is ruled out. The miss is a near-constant
0.0114–0.0124 m/s at every command from 0.065 to 0.111, which only becomes a failing ratio
at the bottom of the band.

**The layer is not in it.** Without the layer, holding `(vx, 0, 0)` for 40 s and reading the
mean after 10 s:

| robot (policy) | command → measured forward (ratio) |
|---|---|
| biped (`runs/g2` 1200, export) | 0 → −0.0064 · 0.065 → 0.0527 (0.81) · 0.10 → 0.0886 (0.89) · 0.16 → 0.1460 (0.91) · 0.24 → 0.2175 (0.91) |
| Go1 (`g2-goto-s20`) | 0 → −0.0128 · 0.40 → 0.348 (0.87) · 0.55 → 0.511 (0.93) · 0.70 → 0.669 (0.96) · 1.0 → 0.977 (0.98) · 1.5 → 1.466 (0.98) |
| leon V concept (`runs/g2` 900) | 0 → 0.0001 · 0.40 → 0.318 (0.79) · 0.55 → 0.499 (0.91) · 0.70 → 0.663 (0.95) · 1.0 → 0.979 (0.98) · 1.5 → 1.446 (0.96) |

The bare policy misses as it does under the layer (biped 0.81 at 0.065, as on point 6).
On every judged leg (`judge-face`, `judge-face.000900`, `judge-export.001200`), each leg under
0.85 is in the bottom sixth of its walk band: leon V's ten all at 0.402–0.452 of 0.4–0.7,
the biped's fifteen all at 0.064–0.079 of 0.064–0.112. The Go1 has none, but its slowest
third still has the lowest ratios (mean 0.909, min 0.870 at 0.40). Its fastest third reaches
0.978 and leon V's 0.971.

**What binds: the tracking kernel is flat where the judge is strict.** The writer's
`tracking_lin_vel` is `exp(-|c - v|² / σ)` with σ = 0.25 (m/s)² on the Go1 and leon V and
0.25 · 0.16² = 0.0064 on the biped (ADR-865 scales it). That is an absolute width of 0.5 m/s
(biped 0.08), while the judge's tolerance is relative: 15% of a 0.4 m/s floor is 0.06 m/s
(biped 0.0098). At the edge of that tolerance the kernel pays 0.986, and on the biped 0.985.
A policy that walks the floor at 0.80 instead of 1.00 therefore loses about 2.5% of a
0.02-weight term, against the walk's effort, clearance and pose terms. The deficit the
policies settle at is roughly absolute (Go1 0.023–0.052 m/s, leon V 0.021–0.082, biped 0.011–0.023),
so it is a failing ratio only at the floor. leon V's 0.433 at 0.5 m/s (constant command,
ADR-862) and the Go1's 0.470 at share 0 are the same miss. The effort-scale hypothesis is not
needed: the 0.65 kg biped shows it at the same relative place. Nothing in this trace shows
whether effort terms or gait quantisation set the 0.01–0.08 m/s itself. What the trace does
show is that the reward does not resist it at the floor.

**The lever, for the next unit.** Make the tracking reward resolve the judge's tolerance at
the band floor. Leave the band, which is the robot's, and the bar alone. The smallest test is
`tracking_lin_vel`'s σ cut to a quarter (an absolute width of 0.25 m/s on leon V, so a 0.06
miss pays 0.94), on leon V's concept, at the G3 budget, judged by `g2_judge.py` at the same
seeds. The expectation: the slowest third's mean deficit falls from 0.062 to at most 0.03
m/s, and every walk leg reaches ≥ 0.85, with run legs still ≥ 0.95. If the deficit does not
move, the binding term is not the kernel but what opposes it (effort, clearance), and the
next test is those weights at the walk band.

**A second finding: 32 of the biped's 37 run legs are never read.** Seed 4's point 0 (run,
side, 0.225 m/s) has 0% of its 4,094 steps within 10° of the point and 4% within 30°. The
biped's yaw limit (0.192 rad/s, the Go1's 1.2 × 0.16) means the layer leaves a turn in place
at 30°, walks diagonally with vy clamped at −0.128, drifts back to 60° and turns again. It
reaches the point, but never on a straight. The 30° exit (ADR-865) closed the loop the layer
was stuck in, but at that yaw rate it still never lines up.

## σ/4 on leon V's concept: the walk passes, the run is lost

The test the step back named. `orun21-lab/g3/leonv-sig4` is `leonv-concept`'s bundle with one
change: `tracking_lin_vel`'s width 0.25 → 0.0625 (m/s)², so √σ = 0.25 m/s and a 0.06 m/s miss
pays 0.94 instead of 0.986. The model, other 12 terms, command, seed and budget are `runs/g2`'s
(1260 iterations, 206.4 M steps, `wall_time_s` 660.7, best reward/step 0.0225 at 1234).
The judge was `g2_judge.py` at the same held-out seeds 0–9, after the 30° exit. **Expected
beforehand:** the bottom third of the walk band (0.4–0.5 m/s) at a mean deficit ≤ 0.03 m/s,
every walk leg ≥ 0.85, every run leg ≥ 0.95.

| policy | pass | reach | hold | falls | walk legs read, min / mean | walk bottom-third deficit m/s | run legs read, under 0.85 |
|---|---|---|---|---|---|---|---|
| `runs/g2` it 900 (σ 0.25, baseline) | 3/10 | 10 | 10 | 0 | 43, 0.801 / 0.894 | 0.070 (15 legs) | 37, 0 |
| σ/4 it 900 | 0/10 | 0 | 10 | 0 | 9, 0.945 / 0.953 | 0.025 (2) | 12, 10 |
| σ/4 it 1200 | 1/10 | 1 | 10 | 0 | 13, 0.985 / 0.990 | 0.007 (2) | 16, 9 |
| σ/4 best (1234) | 1/10 | 1 | 10 | 0 | 13, 0.962 / 0.972 | 0.017 (2) | 17, 9 |
| σ/4 final (1259) | 1/10 | 1 | 10 | 0 | 13, 0.961 / 0.968 | 0.018 (2) | 15, 9 |

(The deficit column is `speed × (1 − ratio)` over walk legs commanded below 0.5 m/s, read from
each seed's `goto.json`. The baseline is the same policy and judge as the 3/10 row above.)

At a constant command (`g3_slowwalk.py --hold-vx`, it 1200, mean after 10 s):

| command m/s | 0.4 | 0.7 | 1.0 | 1.1 | 1.2 | 1.25 | 1.5 |
|---|---|---|---|---|---|---|---|
| σ/4 forward | 0.393 (0.98) | 0.693 (0.99) | 0.987 (0.99) | 1.089 (0.99) | **0.000** | **0.000** | **0.000** |
| σ 0.25 (it 900) | 0.318 (0.79) | 0.663 (0.95) | 0.979 (0.98) | | | | 1.446 (0.96) |

**Read.** The walk half of the expectation held, and better than expected: every walk leg is at
0.96–0.99 and the bottom-third deficit is 0.007–0.025 m/s. So the kernel's width is what set the
slow-walk miss (`kind-ridge-3238`), not effort or gait quantisation. The run half failed. Above
1.1 m/s the policy stands still. Standing at 1.5 pays `exp(-1.5²/0.0625)` ≈ 2e-16, and
running at 1.0 pays `exp(-0.5²/0.0625)` = 0.018, so a policy that has not yet learned to run
gets almost no gradient towards it. The first run point of nine seeds out of ten is never
reached (closest 6.8–7.9 m), and the sequence stops there. One fixed absolute width cannot
serve both: a wide one leaves the walk floor unresolved, a narrow one leaves the run top
unreachable.

**Not put into the writer.** The pass rule was not met, so `cadex_joystick.py` keeps σ 0.25 and
no ADR is written. The next test follows from the read: give the kernel the judge's own shape,
relative to the command. Either sum a wide and a narrow kernel (the wide one keeps the run's
gradient and the narrow one resolves the floor), or use a width proportional to `|c|`. The
expectation for either: walk legs stay ≥ 0.95 as here and run legs return to ≥ 0.95 as at σ 0.25.
