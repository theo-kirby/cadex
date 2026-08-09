---
node_id: f2ea38b9-e2b5-563f-9873-375887f645ee
slug: late-pond-2851
title: The RL training loop and mg-legs
created_at: '2026-08-09T15:22:27+00:00'
parents:
- salty-isle-4063
summary: ''
---
Status: blocked

## Current

Blocked on the **GPU training box**, which runs its own checkout of `training/cadex_train.py` that predates ADR-104. Dispatching the next run (B7) would silently ignore two new draws while recording the new algorithm string in the policy header, so the run is blocked rather than skipped. The CPU sanity run is green: 50 iterations, σ 0.3006, witness 4.07e-08 [rec: western-badger-3023].

What works, and is not in doubt:

- **Training is offboard by design.** `training/` is the one top-level directory that is not part of the product: CMake never installs it, no payload carries it, nothing in it enters `pixi.toml`, and it cannot import Cadex. The engine **verifies** a policy and never **produces** one, which is what keeps it free of an optimiser, an accelerator and even numpy [rec: jolly-walrus-3692] [rec: sage-wood-0687].
- The loop is: author the mechanism in an ordinary xscript project → export MJCF → declare the task → train on the GPU box → verify the returned weights against their witness → roll out locally over twelve seeds. Every step but the last is cheap, which is why a feasibility gate runs before GPU time is bought [rec: humble-path-4466].
- **`mg-legs` is the standing benchmark**: a pelvis and two legs built from MG90S servos. Run **B6** is the first policy in the project's history to step *and* survive — checkpoint 2400 scores 6/12, where every prior run scored zero at every checkpoint [rec: humble-path-4466].
- Selection is by **stepping-and-surviving, not by reward**, for the third measured time [rec: humble-path-4466].

**Still open**: half the episodes at the declared shove band end `tipped`, and backward is the worst direction. B7 is the run that would spend the tenth observation kind — and it is the run the stale checkout blocks [rec: humble-path-4466] [rec: western-badger-3023].

## Negative knowledge

- [scope: reading a trainer reward curve | confidence: high | evidence: humble-path-4466] Trainer reward is not survival, and selecting a checkpoint by reward has lost to selecting by measured behaviour three separate times. Select by stepping-and-surviving.
- [scope: looping evaluators | confidence: high | evidence: humble-path-4466] evaluate_episode multiplies domain randomisation into the model in place and never restores it, so any evaluator that reuses one model across a table drifts its own masses and inertias every episode. Build a fresh model per episode; both engine call sites already do.
- [scope: azimuth and facing direction | confidence: high | evidence: humble-path-4466] azimuth_degrees is about world +X and the engine has no concept of which way a mechanism faces. mg-legs faces +Y, so an entire investigation had its forward and lateral columns swapped. Measure the forward axis off the model rather than assuming it.
- [scope: reward figures recorded before ADR-101 | confidence: high | evidence: humble-path-4466] Every reward figure recorded before the never-ending-episode fix is non-comparable, because it was measured against an unbounded episode. Survival numbers are unaffected.

## Provenance

- western-badger-3023 — the blocker: the GPU box runs its own checkout predating ADR-104
- jolly-walrus-3692 — training/ is offboard by design, with its own pinned venv
- humble-path-4466 — the mg-legs arc, B6, and how a policy is selected
- sage-wood-0687 — why the engine verifies a policy and never produces one
