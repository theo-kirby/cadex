---
node_id: 85087e0f-23b8-58de-9d29-d67ac493f328
slug: long-isle-5502
title: 'ADR-589: tracker normaliser fix; P1 free-ball centring measured, not yet passing'
created_at: '2026-10-07T19:53:38+00:00'
parents:
- peaceful-heron-7678
summary: ''
---
## What

P1, the centring task on a rebuilt ball-plate. A scratch copy, `~/cadex-projects/orun5-ball-plate`, has a free steel sphere rolling by contact on the panel glass. It is read by a `position_tracker` on the plate with a resistive-panel datasheet: range ±80 mm × ±80 mm × (ball height ±3 mm), 0.25 mm resolution, 100 Hz, 0.5 mm noise. There are no sliders and no bead. The ball's velocity is privileged, read by the critic and reward only. The actor reads the tracker and the two STS3215 encoders. The spec bounds M1's `final_distance_mm ≤ 8` and `mean_distance_mm ≤ 15` about the plate centre, with no point goal. Training was flat, and bisecting it found a trainer defect, now fixed as **ADR-589** (commit `a65680ff`). The trainer's running normaliser took its statistics from the noise-free landed readings while the policy acted on noisy ones. It now follows the noisy readings when a task has a tracker, and floors each tracker channel's variance at max(resolution, noise)² for axes and 0.25 for the in-range flag.

## Why

The critic named P1's centring as the next unit, since it is the run's must-have. I did what it asked: a copy, a free ball, a real panel datasheet, M1 bounds, velocity to the critic only, training on the 5090 under the machine lock. The actor reads the encoders rather than an IMU, because the reference rig has no IMU and the STS3215s already report the plate angles. When the grounded policy could not centre, I measured why, as the critic asked. The trainer fix became part of the unit because no tracker task could train at all without it, not even with velocity given to the actor.

## Method

- **Rig and physics.** The scratch project was rebuilt and accepted (revision `6e2cd359`). Run directly in C MuJoCo, the ball settles 4.5 µm into the glass and holds still (0.14 mm/s over 3 s). A 0.6 N, 40 ms kick rolls it at 268 mm/s and off the plate in 0.3 s. MJX's `framepos` with a reference body equals C MuJoCo's at a tilted pose, to 1e-5.
- **First result.** `cadex train` for 300 iterations, 256 envs, seed 12: flat at 0.60 reward per step, with 23–26-step episodes. The policy saturates its tilt with the ball at rest.
- **Bisection** (trainer runs on edited bundles of 120 iterations each, under `flock` on the machine lock):
  - velocity given to the actor: flat (0.61);
  - noise 0: flat;
  - no in-range termination: flat;
  - a ±20 mm z band: flat;
  - world-frame `component_position` plus velocity: **1.31 by 120**;
  - the identical model with only `reftype/refname=c_plate` added: flat.
- **Cause.** Instrumenting the normaliser showed the near-constant ball-z axis at 0.04 mm noise-free spread, read with 0.5 mm noise, reaching the network at up to **51 σ**. With the fix every channel stays within about 7 σ.
- **Measured after the fix** (700 iterations, seed 12, the same bundles):
  - the plate-frame bundle with velocity in the actor: 1.13 at 300 (it was 0.61 before the fix), 1.33 at 700, best 1.37 at 617;
  - **the grounded bundle** (position, flag and encoders only): plateaus at **0.62**, with 131–183-step episodes of 300.
- **Why the world frame learned fast while the plate frame did not.** It is not a bug. The ball sits about 50 mm above the pivot, so in the world frame a tilt moves the reading at once, which is a zero-lag handle on the reward. The panel's own reading responds to tilt only through the double integrator, the real problem.
- **Tests** (`test_dynamics_position_tracker.py`):
  - `tracker_variance_floor` values (pixi);
  - a real trainer run whose flag reads 1 on every step stores the flag's spread at 0.5 or more and each axis at its floor or more, and the engine verifies it. This runs from the training venv: pytest in an overlay at `/tmp/pytest-overlay`, not a repo dependency. Without the fix the flag's spread is **0.0009** and the test fails.
- **Gates:** `pixi run test-engine` 2640 passed / 60 skipped. CLI suite with the GPU hidden: 1217 passed / 1 skipped. The tracker file from the venv: 9 passed.

## Result

True now:
- ADR-589 is in. The trainer can learn from a position tracker.
- The orun5 ball-plate is a free ball on a grounded panel, and its spec judges M1 distance.
- **P1's centring does not pass yet.** A policy reading only grounded channels plateaus at 0.62 reward per step. The same plate-frame rig with the ball's velocity in the actor trains to 1.33, close to the reference's passing 1.41. The missing input is a grounded velocity.
- No `cadex evaluate` was run, because no grounded policy is worth judging. Scratch policies are in `/tmp/bpbis` and in the project's `runs/`, and none is committed.

Next unit, recommended: a grounded velocity for a tracker. This is what a panel's firmware does: it differences successive readings at its rate. The noise is amplified by √2·σ/Δt and the quantisation by Δt, declared rather than privileged (A1). The alternative is an observation history in the trainer. Then retrain P1 centring.

Concerns:
- `cadex smoke` fails this rig on two of its own assumptions:
  - `support` treats the free ball as a robot's free base needing a floor, in a grounded assembly;
  - the `components` check counts the ball's 7.5 µm contact penetration (0.0022 mm³) against a 1e-6 mm³ overlap threshold.
  Both are smoke defects for any rig with a free payload. They are recorded and not fixed.
- An assumption about hops: the ball hops off the glass by up to 3.4 mm under violent random tilts (2 of 64 random episodes), so the ±3 mm band reads it as out of range, as a real panel would.
- The run's must-have, P1, is at risk until the grounded velocity lands.
- Tail: 3 unreconciled records after this one. The charter's reconcile cadence is due, and the critic asked for a reconcile after this record.

Dispatch closed: 1 unit — P1 centring on a free ball measured (grounded policy plateaus at 0.62, needs a grounded velocity); trainer normaliser defect for trackers found and fixed (ADR-589)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: a65680ffe63589adf47cc3eef9310104544663ab

## State Impact

- target: peaceful-orchard-2220 — rig rebuilt in orun5-ball-plate as a free ball read by a position_tracker with M1 distance bounds; grounded policy plateaus at 0.62 reward/step (velocity-in-actor control 1.33); does not pass yet, needs a grounded velocity
- target: chilly-reef-5960 — the trainer's normaliser now follows a tracker's noisy readings and floors its channels (ADR-589, a65680ff); before it no tracker task could train
