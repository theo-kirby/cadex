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

**Implemented, evidence complete** (ADR-588, commit `110e9e6d`; trainer fix ADR-589, commit `a65680ff`) [rec: peaceful-heron-7678] [rec: long-isle-5502]. Reconcile judgement: status `working` — no `met` in the vocabulary, and the human owns the box.

- **Surface**: `assembly.sensor(mount, "position_tracker", name=, range_mm=[[x0,x1],[y0,y1],[z0,z1]], resolution_mm=, rate_hz=, noise_mm=)`, all four datasheet fields required. Grounds observation kind `tracked_position` on another body: `<name>_x/_y/_z` (mm, mount frame) and `<name>_in_range` [rec: peaceful-heron-7678].
- **Engine**: stock `mjSENS_FRAMEPOS` with `reftype=xbody`, `refname=<mount>`. `tracker_reading`: range judged on the true position per axis; inside, (true + noise) rounded to resolution, flag 1; outside, all four read 0. A `jnp` copy lives in `training/cadex_train.py`; engine evaluations draw no noise [rec: peaceful-heron-7678].
- **Trainer**: Gaussian noise of the declared σ into actor and critic inputs; rewards and terminations read the noise-free reading. Since ADR-589 the running normaliser follows the noisy readings and floors each tracker channel's variance at max(resolution, noise)² (0.25 for the flag) — before it, a near-constant axis reached the network at up to 51 σ and **no tracker task could train** [rec: long-isle-5502].
- **Rate**: a tracker slower than the control loop is refused (`tracker_slower_than_control`), never held [rec: peaceful-heron-7678].
- **Tests**: `test_dynamics_position_tracker.py` — mount-frame match within half a resolution step at 5 tilt+turn poses; a ball 250 mm off reads `{0,0,0,0}` and the `_in_range` termination compiles; quantisation and noise-before-rounding; trainer/engine parity on 200 draws, σ within 6%; no ungrounded channels; 30 Hz under a 50 Hz loop refused [rec: peaceful-heron-7678]. Plus the normaliser floor, and a real trainer run storing flag spread ≥ 0.5 (0.0009 without the fix), run from the training venv (9 passed) [rec: long-isle-5502].
- **Trains**: a CPU bundle run fired no ungrounded refusal (witness agreement 1.785e-9) [rec: peaceful-heron-7678].
- **Gates**: `pixi run test-engine` 2640 passed, 60 skipped; CLI (GPU hidden) 1217 passed, 1 skipped [rec: long-isle-5502].
- **Docs**: `docs/XSCRIPT.md`, `docs/MUJOCO.md` sensor table; ledger W1 (sensor landed) [rec: peaceful-heron-7678].

## Negative knowledge

- [scope: position_tracker velocity | confidence: high | evidence: peaceful-heron-7678, long-isle-5502] **No velocity channel, by decision** (ADR-588): neither a touch panel nor a marker camera reports velocity, so under A1 it would be privileged. A firmware-style differenced velocity, declared with its amplified noise, is the recommended next unit [rec: peaceful-heron-7678] [rec: long-isle-5502].

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-s1-grounded-sensor-reads-free)
- peaceful-heron-7678 — position_tracker sensor landed (ADR-588)
- long-isle-5502 — trainer normaliser fix for tracker channels (ADR-589)
