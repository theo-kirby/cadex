---
node_id: 57ef9ebf-21ac-59dc-8596-2d58e433ff5a
slug: golden-garden-8501
title: W2. The ADR-410 walking task is measured end to end
created_at: '2026-09-27T15:18:35+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot10: **W2. The ADR-410 walking task is measured end to end.** One A5 design goes through `cadex walk` training with the unchanged ADR-410 overlay and `--stop-on-collapse`, with its settings and stop rule recorded before it starts. The policy is installed through the supported path, and its gait verdict, W1 video and training curve are published. The bar is `walked = true`. A miss is an honest incomplete result with a diagnosis and a recorded next step. The gait thresholds are not weakened to pass it [rec: damp-dusk-8045].

**Run `w2-1`: walked = false, diagnosed** [rec: bold-reef-1724]:

- Pre-registered in `docs/probes/ot10/README.md` (commit `d94c845f`) before any GPU use. The design is `ot10-quadruped-3` @ `7de6eea6212e`. It won the 15/21 tie with the biped because a quadruped stands without balancing. The run used a `cp -a` copy, so the A5 project stays read-only, with 1000 iterations × 2048 envs, seed 0, a 10,800 s cap, `--stop-on-collapse` confirmed in the trainer argv, grounding enforced and thresholds unchanged. It ran on a local RTX 5090, with no `--prompt`, so no tokens. [rec: bold-reef-1724]
- The walk exited 0 in 2,241.7 s (train 1,944.8 s). There was no collapse. Reward/step rose from 1.16 (iterations 0–99) to 2.62 (900–999), with the best, 2.654, at the last iteration, still rising. Policy `d8b87d2e1215…` was stored, verified against its witness to 1.2e-7, and declared through the walk's own path at revision `f6d32a586ecc…`. [rec: bold-reef-1724]
- Gait: tipped past 45° at 4.36 s (step 218/500). Travel was 97.7 mm: +19 mm forward, −96 mm sideways, heading −52°. Training survival read 0.43. [rec: bold-reef-1724]
- Diagnosis: (1) the policy learned to stand. The speed error averages 0.93/step, and it moves at about 7% of the 80 mm/s target. Under the ADR-410 weights, standing nets about +2/step and walking adds at most +1. (2) The tip falls inside the task's 2–8 s disturbance window, and the review does not record push times. (3) A defect in `training_survival`, recorded on `late-pond-2851`. [rec: bold-reef-1724]
- The gait verdict and curve are published. The W1 video of this policy is not yet rendered. [rec: bold-reef-1724]

**Next (recorded):** render W1's video of `w2-1`, then pre-register a second bounded run warm-started with `--init-from` on the unchanged task digest, with the same thresholds. A reward change would need a new design turn, not an actor edit [rec: bold-reef-1724].

## Negative knowledge

- [scope: ADR-410 reward weights on ot10-quadruped-3, 1000×2048, seed 0 | confidence: medium | evidence: bold-reef-1724] Standing out-earns walking under these weights (about +2/step standing against at most +1 more for walking), and a from-scratch run of this size converged on standing. This is one run of evidence, not a general claim about the overlay.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- bold-reef-1724 — W2 run w2-1: pre-registered, trained 1000×2048 on a copy of ot10-quadruped-3, walked=false, diagnosed
