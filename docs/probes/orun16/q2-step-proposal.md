# orun16 Q2: O1 proposal, leo's solver step from 2 ms to 1 ms (not built)

Verified against source: 2026-10-22. Frozen evidence (orun16, iteration 19).
Written before any build, as O1 asks. **Not built**: SG and RL hold the GPU
and rank above Q2, and the change forces every later policy to train cold.

## The measurement

- **The gap.** The front push-rod loops (`j_frodbot_*`) open past O9's
  2 mm on every judged leo-v05 policy: v05-s1-50 3.02 / 3.27 mm (L / R),
  sg-s8-25 2.9 / 3.2 / 3.7 mm at 1000 / 1700 / 2400 (`q2-rod-solver.md`,
  `sg-s8-25.md`). The hind loops stay under 1.8 mm.
- **The cause** (`rod_fight.py`, v05-s1-50, seeds 1001–1003): fore stance
  with the wrist drive saturated; the loop carries 0.9–1.3 kN of paw load
  and its ends separate at ~0.5 m/s. The loop's equality is a critically
  damped spring-damper at two solver steps (4 ms), so a stance impulse
  opens it by about speed × τ; its static softness accounts for 11–16 µm.
- **What does not close it** at 2 ms: stiffer carpus / wrist stops
  (`carpus4`, `stop4`: 2.8–3.3 mm, −0.17 m/s), 4× the iterations at
  1e-12 tolerance (3.08 / 3.26 mm), a rod loop at one step (`eq2`: blows
  up on 10/10 seeds in 14 steps).
- **What does** (same policy, patched in memory, all 10 seeds):

  | variant | front loop max L / R mm | top 2 s m/s |
  |---|---|---|
  | base (2 ms, loops 4 ms) | 3.02 / 3.27 | 2.39 |
  | dt1keep (1 ms, loops 4 ms) | 1.11 / 0.92 | 0.85 |
  | dt1 (1 ms, every equality 2 ms: the build) | 0.39 / 0.47 | 0.83 |

  At the same 1 ms step, halving the loop's time constant (4 → 2 ms) cut
  the max ~2.2×. The policy trained at 2 ms shuffles on the 1 ms plant, so
  the dt1 rows are at a gait with the wrist off peak, not the gallop's.

## The change

One literal in leo's `script.py`: `assembly.mjcf(..., solver_step_s=0.001)`
(leo is at 64 parameters, so not a knob). The engine then sets every
equality's `solref` at its two-step floor, 0.002 s (ADR-724's rule);
contacts stay at `CONTACT_TIMECONST_S` 0.004 s and the paw pins' stops at
their declared 0.004 s; the task's episode becomes 20 solver steps an
action at the same 50 Hz control (500 × 20 = 10,000 solver steps an
episode, under `MAXIMUM_SOLVER_STEPS` 2,000,000). No part, joint, mass or
drive moves, so the clearance sweep and static pairs cannot change; the
build is still run and its gates read against leo-v05's baseline. Tag
`leo-v05.1`.

## The expected effect

- **The gap at a gallop.** The loop opens by separation speed × τ. At a
  gallop the separation speed is the 2 ms model's (~0.5 m/s) or close to
  it, and τ halves (4 → 2 ms), so the expected front max is about half of
  today's: **1.5–1.9 mm** from 3.0–3.7, under O9's 2 mm with little margin
  at 2400 (3.7 → ~1.9). The dt1 shuffle's 0.39–0.47 mm is the floor, not
  the forecast.
- **The gait.** The contact time constant is unchanged, so the feet sink as
  before; the pin's spring, damping and stops are unchanged. Nothing in the
  plant should cost speed once retrained, but the 2 ms policies' 0.85 m/s
  on it says the policy is tuned to the 2 ms dynamics: no current
  checkpoint carries over.
- **Risk.** If the loop still opens past 2 mm at 2400, the remaining lever
  is O1 candidate (b) in `q2-rod-solver.md`, a front linkage that does not
  carry the stance load through the rod (the owner's linkage leg: its own
  record and an R1 note).

## The retrain cost

- **Solver cost.** `step_cost.py` on sg-s9's model (CPU, zero control,
  2 s simulated, best of 3): 17.7 ms wall per simulated second at 2 ms,
  32.1 ms at 1 ms, **1.81×**.
- **Per iteration.** leo iterates at ~65–70 s at 4096 envs on the 2 ms
  model (sg-s8: ~65 s; sg-s9 timed below in this iteration's report). With
  the physics most of an MJX iteration, the forecast is **~120–130 s**
  (1.8× of the physics, the PPO update unchanged); a 50-iteration screen
  goes from ~1 h to ~1.8 h plus the ~6 min compile. It is measured on the
  first ten iterations of the first 1 ms bundle, and `budget_s` set from
  that (O8).
- **Every later policy trains cold.** The trainer refuses a warm start
  across a model change, so the SG line (sg-s9 onward) restarts on
  leo-v05.1, and every P1/P2 screen after it runs at ~1.8× the GPU time.
  That is why it waits until the SG/RL question is settled at 2 ms: the
  levers learnt there (`heel_sched`, `overrun`, `hind_scuff`, the 700
  stride) carry over as task terms, the checkpoints do not.

## How it is judged (O1)

The screen it is meant to fix: hk12-s1's task (the gallop task at
`leo-v05`), cold, seed 0, 4096 envs, 50 iterations, on leo-v05.1, judged
at 25 and 50 on the 10 frozen seeds with `orun14/rod_gap.py`,
`rod_fight.py`, `paw_floor.py`, `orun12/legs.py`, `orun13/p2_lag.py`,
against v05-s1-50 (the same task cold on leo-v05: 2.39 m/s, front max
3.02 / 3.27 mm). **Kept only if** the front loops' max is at most 2 mm on
both legs with frames from 1 s, and the top 2 s speed, U and rotary count
are no worse than v05-s1-50's by more than its seed spread.
