---
node_id: 32a1444d-3d99-57c2-a648-5da32370d5cf
slug: chilly-reef-5960
title: S1. A grounded sensor reads a free body's position
created_at: '2026-10-07T17:58:00+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun5: **S1. A grounded sensor reads a free body's position.** A sensor kind measuring a body's position (optionally velocity) in a named component's frame, declaring range, resolution, rate and noise (A1) that the trainer applies; out of range reads as out of range, never stale or clamped; described in `describe_api`, `docs/XSCRIPT.md`, `docs/MUJOCO.md`; tested through a tilt and turn, out of range, noise and quantisation, and training without the ungrounded refusal. The human owns the checkbox [rec: honest-bay-2056].

**Implemented, evidence complete, now with velocity** (ADR-588 `110e9e6d`; trainer fix ADR-589 `a65680ff`; velocity ADR-590 `e2574ac4`) [rec: peaceful-heron-7678] [rec: long-isle-5502] [rec: smooth-stream-7287]. Reconcile judgement: status `working` — no `met` in the vocabulary, and the human owns the box.

- **Surface**: `assembly.sensor(mount, "position_tracker", name=, range_mm=[[x0,x1],[y0,y1],[z0,z1]], resolution_mm=, rate_hz=, noise_mm=)`, all four datasheet fields required. Grounds `tracked_position` on another body: `<name>_x/_y/_z` (mm, mount frame) and `<name>_in_range` [rec: peaceful-heron-7678]. It also grounds `tracked_velocity` (`assembly.observation(body, "tracked_velocity", name=, sensor=tracker)`, mm/s), which must follow a position from the same tracker on the same body (`observation_tracker_velocity_unpaired`) [rec: smooth-stream-7287].
- **Engine**: stock `mjSENS_FRAMEPOS` with `reftype=xbody`, `refname=<mount>`. `tracker_reading`: range judged on the true position per axis; inside, (true + noise) rounded to resolution, flag 1; outside, all four read 0 [rec: peaceful-heron-7678]. Velocity is a stateless `framelinvel` in the mount frame (exact derivative of the tracked position, rotation included; probe matched finite differences in C MuJoCo and MJX), noise √2·noise_mm·rate_hz, quantum resolution_mm·rate_hz, zeros whenever the paired position is out of range. It omits a difference's half-interval lag and successive-noise anticorrelation, both named in `docs/MUJOCO.md` [rec: smooth-stream-7287]. Engine evaluations draw no noise [rec: peaceful-heron-7678].
- **Trainer**: `jnp` copies of both readings; Gaussian noise of the declared σ into actor and critic inputs; rewards and terminations read noise-free values. The running normaliser floors each sensor channel's variance at max(quantum, noise)² (0.25 for the flag) — before ADR-589 no tracker task could train [rec: long-isle-5502] [rec: smooth-stream-7287].
- **Rate**: a tracker slower than the control loop is refused (`tracker_slower_than_control`), never held [rec: peaceful-heron-7678].
- **Tests**: `test_dynamics_position_tracker.py` — mount-frame match within half a resolution step at 5 tilt+turn poses; out of range reads zeros; quantisation and noise; trainer/engine parity on 200 draws; slow tracker refused [rec: peaceful-heron-7678]; normaliser floor and a real trainer run [rec: long-isle-5502]; velocity within half a quantum of the true plate-frame derivative through a moving tilt and turn, zeros out of range, declared noise and quantum, parity, unpaired refusals, and the jitted trainer path (12 passed from the training venv) [rec: smooth-stream-7287].
- **Proved in use**: P1's centring trains and passes on the position and velocity channels [rec: smooth-stream-7287].
- **Gates**: `pixi run test-engine` 2643 passed, 60 skipped; CLI (GPU hidden) 1217 passed, 1 skipped [rec: smooth-stream-7287].
- **Docs**: `docs/XSCRIPT.md`, `docs/MUJOCO.md` sensor table, `describe_api` (trimmed to fit) [rec: peaceful-heron-7678] [rec: smooth-stream-7287].

## Negative knowledge

- [scope: position_tracker velocity form | confidence: high | evidence: smooth-stream-7287] A velocity carried as the previous reading in state was not built: it would add trainer carried state, make engine `observation_values` stateful, and touch rewards and terminations; the stateless `framelinvel` keeps the same declared noise, quantum, range rule and parity (ADR-590) [rec: smooth-stream-7287].

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-s1-grounded-sensor-reads-free)
- peaceful-heron-7678 — position_tracker sensor landed (ADR-588)
- long-isle-5502 — trainer normaliser fix for tracker channels (ADR-589)
- smooth-stream-7287 — tracked_velocity, the tracker's grounded differenced velocity (ADR-590); supersedes the "no velocity channel" decision of ADR-588
