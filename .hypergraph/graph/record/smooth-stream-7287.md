---
node_id: 7b829f31-9d97-5532-8d47-ce45695db283
slug: smooth-stream-7287
title: 'ADR-590: tracked_velocity; P1 free-ball centring passes its M1 spec 8/8'
created_at: '2026-10-07T20:23:55+00:00'
parents:
- long-isle-5502
summary: ''
---
## What

A grounded velocity for a position tracker (**ADR-590**, commit `e2574ac4`), followed by P1's centring retrained and judged with it. A `position_tracker` now also grounds `tracked_velocity`: `assembly.observation(body, "tracked_velocity", name=..., sensor=tracker)` reads `<name>_x/_y/_z` in mm/s. This is the velocity a panel's firmware reports by differencing successive readings `1/rate_hz` apart. It uses the tracker's existing datasheet:
- noise is `sqrt(2)·noise_mm·rate_hz`;
- the quantum is `resolution_mm·rate_hz`;
- it reads zeros whenever the paired `tracked_position` reads `_in_range` 0.

**P1 centring now passes its M1 spec on 8 of 8 seeds.**

## Why

The critic named this unit: P1 is the run's must-have, and it failed for want of a grounded velocity. I did what it asked, with one deliberate change of form, recorded in ADR-590.

**What I changed.** The velocity is a stateless `framelinvel` in the mount frame, which is the exact derivative of the tracked position, frame rotation included. It carries the declared noise √2·σ/Δt and the quantum res/Δt, with Δt = 1/rate_hz as the critic specified. I did not literally carry the previous reading in state.

**Why.** Carrying the previous reading would have added a member to the trainer's carried state, made the engine's `observation_values` stateful, and touched rewards and terminations. The stateless form keeps the same declared noise, the same resolution, the same out-of-range rule and the same engine/trainer parity.

**What it leaves out.** It does not model the half-interval lag of a difference (5 ms here) or the anticorrelation of noise between successive differences. `docs/MUJOCO.md` names both.

**Two other notes.**
- **describe_api.** Trimmed, not raised: one restating sentence came out of the assembly notes to pay for the new kind.
- **Observation history.** Not tried. Centring passed, so it was not needed.

## Method

- **Probe.** In C MuJoCo 3.10 and in MJX, `framelinvel` with `reftype=xbody` equals the finite-difference derivative of `framepos` with the same reference on a rotating, tilting plate: [0.46, −0.09, 0.06] both ways.
- **Engine.** `OBSERVATION_KINDS["tracked_velocity"]` is added. `observation_records` refuses a velocity that has no earlier position from the same tracker of the same body (`observation_tracker_velocity_unpaired`), and stores `in_range_of`. `task_records` carries `in_range_of`. `tracker_velocity_noise` and `tracker_velocity_reading` are new. `observation_values` gates the velocity on the paired flag.
- **API.** `position_tracker` measures both kinds, and a `tracked_velocity` must name a sensor. The `sensor()` docstring and the describe_api notes were updated.
- **Trainer.** `tracker_velocity_noise` and `tracker_velocity_reading` are `jnp` copies. `observe()` gates on the paired flag. `tracker_noise_std` and `tracker_variance_floor` take the velocity's spread and quantum.
- **Smoke runner.** It gets the noise-free copy.
- **Tests** (`test_dynamics_position_tracker.py`, 3 new and 1 extended):
  - the surface and three unpaired refusals;
  - through a tilt and a turn with the plate moving, the velocity is within half a quantum of the true plate-frame derivative, and out of range it reads zeros;
  - noise and quantum follow the declaration, and the trainer's copy equals the engine's on 200 draws with the declared spread;
  - the real-trainer test now runs a velocity through the trainer's jitted path and stores its normaliser spread at or above the floor.
- **Project.** In `orun5-ball-plate`, the panel's velocity `bd` was added to the actor's inputs. The ball's world velocity stays privileged, for the reward and the critic only. I ran `cadex train --task task_centre --iterations 700 --envs 256 --seed 12` on the 5090 (326 s), declared the best checkpoint as `policy_centre`, and ran `cadex evaluate`.

## Result

**What is true now:**
- ADR-590 is in. A tracker's differenced velocity is a grounded channel.
- **Training reward per step, seed 12**, as training-batch means on noisy readings:

  | Iteration | Reward per step |
  |---|---|
  | 0 | 0.74 |
  | 137 | 0.61 |
  | 274 | 0.99 |
  | 410 | 1.05 |
  | 535 (best) | **1.13** |
  | 684 | 1.10 |
  | final | 1.08 |

  That is up from the 0.62 plateau without a velocity, but below 1.33 (the ball's true velocity in the actor) and 1.41 (the reference rig). Episodes reach the 300-step horizon from about iteration 270.
- **`cadex evaluate` against the M1 spec: pass, 8 of 8 seeds** (policy `9cb0a64c6ca1`, evaluation `71e1646bdacd-9cb0a64c6ca1`):
  - `final_distance_mm` 1.20–2.64 against a bound of 8;
  - `mean_distance_mm` 3.11–6.41 against a bound of 15;
  - all 8 seeds ran to the horizon, through the start kick and the mid-episode shove.
- **Committed images.** The hero and the seed-9001 filmstrip are in `docs/probes/orun5/` (`p1-centring-hero.png`, `p1-centring-seed-9001.png`, 160 KB and 152 KB). The ledger marks W1 and W2 as replaced.
- **Gates:**
  - `pixi run test-engine`: 2643 passed, 60 skipped. The only later change is to the tracker test file, which passes 11, with 1 skipped, under pixi.
  - The tracker tests from the training venv: 12 passed.
  - CLI suite with the GPU hidden: 1217 passed, 1 skipped.
  - No protocol or payload change.

**Concerns:**
- **The evaluation is noise-free.** Engine evaluations draw no tracker noise (ADR-588), so the pass is judged on clean panel readings while training saw a velocity noise of 70.7 mm/s. A noisy-readings evaluation would make P1's claim stronger, and it is worth a unit before C1.
- **The circle task is not rebuilt yet.** P1's second half is open: the circle task's spec bounding M1's laps, failing a rocking trace and passing a circling one.
- **Smoke defects remain.** The two smoke defects for a free payload, recorded in `long-isle-5502`, are still open.
- **Scratch files.** The scratch policies are in the project's `runs/` and `assets/`, and none is committed.

**Next, recommended:** S2, the load sensor, which is next in the charter's priority order. Alternatively, P1's circle-task spec, to finish P1.

**Tail:** 1 unreconciled record.

Dispatch closed: 1 unit — ADR-590 tracked_velocity (grounded differenced velocity); P1 free-ball centring passes its M1 spec 8/8 seeds (train best 1.13 reward/step)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: e2574ac4220cff77a5dc9854a391800e09c94bfc

## State Impact

- target: peaceful-orchard-2220 — P1 centring passes: free ball on a grounded panel with the panel's differenced velocity (ADR-590) trains to 1.13 reward/step (seed 12, best of 700 it) and cadex evaluate passes the M1 spec 8/8 seeds (final 1.20-2.64 mm, mean 3.11-6.41 mm); evaluation is noise-free; circle task not yet rebuilt
- target: chilly-reef-5960 — a position_tracker also grounds tracked_velocity (ADR-590, e2574ac4): framelinvel in the mount frame, noise sqrt(2)*noise_mm*rate_hz, quantum resolution_mm*rate_hz, zeros when the paired position is out of range; engine/trainer parity tested
