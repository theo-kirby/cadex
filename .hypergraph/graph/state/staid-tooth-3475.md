---
node_id: de11b110-e5bb-5b0a-9481-031028136fa0
slug: staid-tooth-3475
title: R3. A balancer balances in place and recovers from a shove
created_at: '2026-09-30T07:04:58+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run ot11: **R3. A balancer balances in place and recovers from a shove.** - The final pre-registered confirmation evaluation passes the frozen balance spec on every seed: upright, within position and heading bounds, and recovering from the declared shoves. - The judge's bar is met. - Robin (ot8/ot9) or a new balancer is copied into an `ot11-*` project. Robin's baseline policy is the ot9 one, and it stays read-only. [rec: kind-spire-3578]

Declared target: `gap-r3-balancer-balances-place-recovers`. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: kind-spire-3578].

**R3's measured bar is reached; the owner ticks it** [rec: even-otter-4624]. Status flipped to working on that measured, causally parented evidence; the checkbox remains the owner's.

- **Policy.** `8919a22d…` on `ot11-robin-1` (accepted revision `cbf14e3c…`), the iteration-400 checkpoint of the 900 s run `bal-1`, trained by the product agent through the loop in one round [rec: southern-quartz-3293]. The ot9 baseline (drift ~16 COM heights, 131° turn) stays read-only in `ot9-robin` [rec: southern-quartz-3293].
- **Confirmation 1** (registration `c2dd99bb`, committed before running; results `413487bc`): passes B1–B5 on all ten frozen seeds, none void. Worst per predicate: B2 tilt 11.5° (limit 30), B3 drift 0.92 COM heights (limit 2.0), B4 heading 0.97° (limit 20), B5 recovery 0.42 s (limit 2.0); B1 all ten ran 10 s. Metrics equal bal-1's round evaluation exactly — the rollout is deterministic per frozen seed, so the confirmation reproduces rather than resamples [rec: even-otter-4624].
- **Blind judge** (`runner/judge.py balance`, three calls a seed, claude-opus-5-5): bar met on 1101/1105/1110 with totals 12, 12, 11; spec and judge agree [rec: even-otter-4624].
- **Evaluation trust settled** (commit `4b4b03e8`): over 200 states MJX and MuJoCo sensordata agree to float32 rounding on every policy channel (worst gyro 0.0003 deg/s of 826), so trainer and rollout observe the same inputs (`runner/obs_parity.py`, receipt `retained/r3-robin-1-obs-parity.json`) [rec: soft-otter-1938].
- **Assumption, recorded:** the IMU (declared on the Pi board component) and wheel encoders (declared on the joints) stay declared rather than modelled, under ADR-408; R3's "accepted design" is taken not to require those parts modelled. The gyro channel reads world frame — a sim-to-real fact for a later rung, not an R3 blocker [rec: soft-otter-1938].

## Negative knowledge

None yet.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
- southern-quartz-3293 — a training round: policy 8919a22d passes the frozen balance spec on 10 of 10 seeds; undeclared-part sensor concern
- soft-otter-1938 — evaluation trust: MJX/MuJoCo observation parity measured; sensors stay declared (assumption recorded)
- even-otter-4624 — pre-registered confirmation 1: 10 of 10 seeds pass, judge bar met (12, 12, 11); R3's measured bar reached
