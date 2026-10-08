---
node_id: d722c799-91fc-5ea6-80eb-045cd51dd901
slug: peaceful-heron-7678
title: 'ADR-588: position_tracker, a grounded sensor for a free body''s position (S1)'
created_at: '2026-10-07T18:53:55+00:00'
parents:
- dusty-meadow-8719
summary: ''
---
## What

S1, the grounded position sensor (ADR-588, commit `110e9e6d`). `assembly.sensor(mount, "position_tracker", name=..., range_mm=[[x0,x1],[y0,y1],[z0,z1]], resolution_mm=..., rate_hz=..., noise_mm=...)` declares a touch panel or a marker camera on the component it is mounted on, with all four datasheet fields required (charter A1). It grounds a new observation kind, `tracked_position`, on *another* body: channels `<name>_x/_y/_z` (the body's position in the mount's frame, mm) and `<name>_in_range`.

## Why

The critic named S1 as the next unit, and it is the highest-ranked open criterion (`chilly-reef-5960`). P1 depends on it. I did what the critic asked, with two deliberate narrowings, both recorded in ADR-588:
- **No velocity channel.** Neither a touch panel nor a marker camera reports velocity, so under A1 it would be privileged.
- **The rate is a refusal, not a hold.** A tracker slower than the control loop is refused at export. A sample-and-hold would feed the policy stale readings, which the criterion forbids.

## Method

- **Engine.** `OBSERVATION_KINDS["tracked_position"]` is a stock `mjSENS_FRAMEPOS` on the body's xbody, with `reftype=xbody` and `refname=<mount>`. MuJoCo therefore computes the position in the mount's frame. `tracked_position` also has one derived suffix, `_in_range`.
- **Task row.** It carries `frame` and `tracker`. It has four channels over a three-value `sensordata` slice.
- **`tracker_reading`.** The engine's `observation_values` applies it.
  - Range is judged on the true position, on every axis.
  - Inside the range, the reading is (true + noise) rounded to the resolution, and the flag is 1.
  - Outside the range, all four values read 0.
- **Copies of that function.** There is a `jnp` copy in `training/cadex_train.py`, because the trainer cannot import the engine. The smoke runner has a no-noise copy so terminations can name the flag.
- **Trainer noise.** Gaussian noise of the declared σ is drawn from a key split that only a task with a tracker takes. It goes into the actor and critic input. Rewards and terminations read the noise-free reading. Engine evaluations draw no noise.
- **Rate check.** `_check_tracker_rates` refuses `rate_hz` below `1/control_interval_s` (`tracker_slower_than_control`).
- **Surface.** The tracker's mount travels as the observation's second argument, so the worker can name the frame. `_observations` checks that the mount is in the assembly.
- **describe_api.** I trimmed two restating sentences from the assembly notes. The assembly page measured 21,539 characters against the 21,500 budget before the trim, and the gate test passes after it.
- **Docs.** `docs/XSCRIPT.md`, `docs/MUJOCO.md` (sensor table and a paragraph), ADR-588, and ledger row W1 (sensor landed; rig open).

## Result

What is true now:
- **Tests.** `test_dynamics_position_tracker.py` has 7 tests:
  - The surface: the declaration and the mount, and the refusals.
  - Through a tilt and a turn: on a plate that turns about z and tilts about x, the channel matches the ball's true position in the plate frame (computed from `xpos`/`xmat`) within half a resolution step at 5 poses, all in range.
  - Out of range: a ball 250 mm off the plate reads `{0,0,0,0}`, and the termination on `ball_in_range` compiles.
  - Quantisation, and noise added before rounding.
  - The trainer's copy equals the engine's on 200 random draws. The trainer's noise spread is the declared σ within 6%.
  - The task has no ungrounded channels, and a 30 Hz tracker under a 50 Hz loop is refused.
  - `test_dynamics_task_api` was updated for derived suffixes.
- **Trains.** The test rig exported as a bundle and trained on CPU with `~/cadex-train-venv`: 3 iterations, 8 envs, witness agreement 1.785e-9. The ungrounded refusal did not fire. Episodes ran 3–5 steps, because the bare rig gives the ball nothing to rest on, so it falls out of z-range and the termination fires in the trainer as well.
- **Gates.**
  - `pixi run test-engine`: 2639 passed, 59 skipped, both before and after the notes trim.
  - `pixi run build-engine`, then the CLI suite with the GPU hidden (`CUDA_VISIBLE_DEVICES= JAX_PLATFORMS=cpu`): 1217 passed, 1 skipped.
  - No protocol or payload change, so the packaged gate was not needed.

Concerns for the next iteration:
- **P1 has no velocity channel.** A memoryless MLP centring a ball reads its position but not its speed. Options: also observe the plate's IMU, or add a differencing model in a later unit (named honestly), or accept a privileged velocity for the critic only. Decide in P1 and record the choice.
- **describe_api's assembly page is still near its budget.** The trim freed about 30 characters of net headroom. The next surface addition (S2, R1, L1) must trim or split the page within its own unit.
- The unreconciled tail is now two records (`dusty-meadow-8719` and this one).

Dispatch closed: 1 unit — S1 position_tracker sensor (ADR-588), gates green

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: 110e9e6d096345f94e43cfa13386603e67e3de13

## State Impact

- target: chilly-reef-5960 — S1's capability landed (ADR-588, commit 110e9e6d): position_tracker sensor with a datasheet (range/resolution/rate/noise), tracked_position in the mount frame via framepos+reftype, out-of-range reads zeros with <name>_in_range 0, trainer applies noise and quantisation, slow tracker refused; 7 tests incl. tilt+turn match and trainer/engine parity; CPU training on a tracked task ran without the ungrounded refusal. No velocity channel (privileged under A1).
