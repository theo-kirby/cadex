---
node_id: 33108d6e-97da-5fc5-ba04-35283c474e07
slug: peaceful-orchard-2220
title: P1. The ball-plate, rebuilt as built
created_at: '2026-10-07T17:58:13+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun5: **P1. The ball-plate, rebuilt as built.** On a scratch copy (`orun5-ball-plate`) the ball is a free sphere rolling on the plate by contact, read by an S1 touch panel, no sliders or hidden bead; the centring task trains and passes its spec with distance from centre measured by M1 (no point goal); the circle task's spec bounds M1 laps so rocking fails it — trained to a pass if time allows, else the record shows the predicate failing rocking and passing circling; pushrods (L1) optional. The human owns the checkbox [rec: honest-bay-2056].

**Centring passes; the circle half is open** [rec: smooth-stream-7287]. The run's must-have — a real ball on a real plate, read by a grounded sensor, trains centring to a pass — is evidenced, on noise-free evaluation readings.

- **Rig** (revision `6e2cd359`, accepted): free steel sphere on the panel glass, read by a `position_tracker` with a resistive-panel datasheet (±80 × ±80 mm × ball height ±3 mm, 0.25 mm, 100 Hz, 0.5 mm noise). Spec: M1 `final_distance_mm ≤ 8`, `mean_distance_mm ≤ 15` about the plate centre, no point goal [rec: long-isle-5502] [rec: dusty-meadow-8719]. Since ADR-590 the actor reads the tracker's position, its differenced velocity `bd` and the two STS3215 encoders; the ball's world velocity stays privileged to critic and reward [rec: smooth-stream-7287].
- **Physics checked**: in C MuJoCo the ball rests 4.5 µm into the glass; MJX `framepos` with a reference body matches C MuJoCo to 1e-5 [rec: long-isle-5502].
- **Trained** (seed 12, 700 iterations, 256 envs, 326 s on the 5090): best **1.13** reward/step at iteration 535, up from the 0.62 plateau without a velocity, below 1.33 (true velocity in the actor) and the reference's 1.41; episodes reach the 300-step horizon from ~iteration 270. Best checkpoint declared `policy_centre` [rec: smooth-stream-7287].
- **Evaluated**: `cadex evaluate` passes the M1 spec **8/8 seeds** (policy `9cb0a64c6ca1`, evaluation `71e1646bdacd-9cb0a64c6ca1`): final 1.20–2.64 mm (bound 8), mean 3.11–6.41 mm (bound 15), all to the horizon through the start kick and mid-episode shove. Hero and seed-9001 filmstrip in `docs/probes/orun5/` [rec: smooth-stream-7287].
- **Not done**: the circle task (spec bounding M1 laps, failing rocking, passing circling); a noisy-readings evaluation of the centring policy (engine evaluations draw no tracker noise, training saw 70.7 mm/s velocity noise); scratch policies are uncommitted, in the project's `runs/` and `assets/` [rec: smooth-stream-7287].

## Negative knowledge

- [scope: orun5-ball-plate centring | confidence: high | evidence: long-isle-5502] A world-frame position reading learns fast only because the ball sits ~50 mm above the pivot, giving tilt a zero-lag handle; the panel-frame reading sees tilt only through the double integrator. Not a bug [rec: long-isle-5502].
- [scope: orun5-ball-plate centring | confidence: high | evidence: long-isle-5502, smooth-stream-7287] Without a grounded velocity the grounded actor plateaus at 0.62 reward/step; the missing input was the velocity, not noise, termination or z band (bisected) [rec: long-isle-5502] [rec: smooth-stream-7287].
- [scope: cadex smoke on rigs with a free payload | confidence: high | evidence: long-isle-5502, smooth-stream-7287] `cadex smoke` fails rigs with a free payload: `support` treats the ball as a free base needing a floor, and `components` counts its 7.5 µm contact penetration against a 1e-6 mm³ threshold. Still open [rec: long-isle-5502] [rec: smooth-stream-7287].
- [scope: evaluation rigs with a free payload | confidence: medium | evidence: dusty-meadow-8719] `evaluation_rig` reads a lone free ball as the base; two free bodies are refused [rec: dusty-meadow-8719].
- [scope: orun5-ball-plate tracker z band | confidence: high | evidence: long-isle-5502] The ball hops off the glass by up to 3.4 mm under violent random tilts, reading out of range as a real panel would [rec: long-isle-5502].

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-p1-ball-plate-rebuilt-as)
- dusty-meadow-8719 — M1 lets P1's spec bound distance without a point goal
- long-isle-5502 — rig rebuilt on a free ball and tracker; grounded centring plateaus at 0.62
- smooth-stream-7287 — with the tracker's grounded velocity, centring trains to 1.13 and passes its M1 spec 8/8 seeds
