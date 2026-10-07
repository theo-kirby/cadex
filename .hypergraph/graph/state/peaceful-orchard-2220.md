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

**Rig rebuilt; centring measured, does not pass yet — the run's must-have is at risk** [rec: long-isle-5502].

- **Rig** (revision `6e2cd359`, accepted): free steel sphere on the panel glass, read by a `position_tracker` with a resistive-panel datasheet (±80 × ±80 mm × ball height ±3 mm, 0.25 mm, 100 Hz, 0.5 mm noise). Actor reads the tracker and the two STS3215 encoders; ball velocity is privileged to critic and reward only. Spec: M1 `final_distance_mm ≤ 8`, `mean_distance_mm ≤ 15` about the plate centre, no point goal [rec: long-isle-5502]. M1 made that spec possible [rec: dusty-meadow-8719].
- **Physics checked**: in C MuJoCo the ball rests 4.5 µm into the glass (0.14 mm/s drift over 3 s); MJX `framepos` with a reference body matches C MuJoCo to 1e-5 [rec: long-isle-5502].
- **Measured** (700 iterations, seed 12, after ADR-589): grounded actor plateaus at **0.62** reward/step (131–183-step episodes of 300); the same plate-frame rig with velocity in the actor reaches 1.33 (best 1.37), near the reference's passing 1.41. The missing input is a grounded velocity [rec: long-isle-5502].
- **Not done**: no `cadex evaluate` run (no grounded policy worth judging); no policy committed; circle task not started [rec: long-isle-5502].
- **Recommended next**: a grounded tracker velocity, differenced at the panel's rate as firmware does, with noise √2·σ/Δt declared (A1); alternative, an observation history in the trainer. Then retrain centring [rec: long-isle-5502].

## Negative knowledge

- [scope: orun5-ball-plate centring | confidence: high | evidence: long-isle-5502] A world-frame position reading learns fast (1.31 by 120 iterations) only because the ball sits ~50 mm above the pivot, giving tilt a zero-lag handle; the panel-frame reading sees tilt only through the double integrator. Not a bug. Bisected [rec: long-isle-5502].
- [scope: orun5-ball-plate centring before ADR-589 | confidence: high | evidence: long-isle-5502] Bisection before ADR-589 — velocity in actor, zero noise, no in-range termination, ±20 mm z band — all flat (~0.6); the cause was the normaliser, not these [rec: long-isle-5502].
- [scope: cadex smoke on rigs with a free payload | confidence: high | evidence: long-isle-5502] `cadex smoke` fails rigs with a free payload: `support` treats the ball as a free base needing a floor in a grounded assembly, and `components` counts its 7.5 µm contact penetration (0.0022 mm³) against a 1e-6 mm³ threshold. Recorded, not fixed [rec: long-isle-5502].
- [scope: evaluation rigs with a free payload | confidence: medium | evidence: dusty-meadow-8719] `evaluation_rig` reads a lone free ball as the base; two free bodies are refused [rec: dusty-meadow-8719].
- [scope: orun5-ball-plate tracker z band | confidence: high | evidence: long-isle-5502] The ball hops off the glass by up to 3.4 mm under violent random tilts (2 of 64 episodes), reading out of range as a real panel would [rec: long-isle-5502].

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-p1-ball-plate-rebuilt-as)
- dusty-meadow-8719 — M1 lets P1's spec bound distance without a point goal
- long-isle-5502 — rig rebuilt on a free ball and tracker; grounded centring plateaus at 0.62
