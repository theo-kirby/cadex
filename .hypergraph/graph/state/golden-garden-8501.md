---
node_id: 57ef9ebf-21ac-59dc-8596-2d58e433ff5a
slug: golden-garden-8501
title: W2. The ADR-410 walking task is measured end to end
created_at: '2026-09-27T15:18:35+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run ot10: **W2. The ADR-410 walking task is measured end to end.** One A5 design goes through `cadex walk` training with the unchanged ADR-410 overlay and `--stop-on-collapse`, with its settings and stop rule recorded before it starts. The policy is installed through the supported path, and its gait verdict, W1 video and training curve are published. The bar is `walked = true`. A miss is an honest incomplete result with a diagnosis and a recorded next step. The gait thresholds are not weakened to pass it [rec: damp-dusk-8045].

**`walked = true` evidence exists; the owner ticks it** [rec: mild-lily-4405]. Run `w2-2` on `ot10-quadruped-3`, re-reviewed under ADR-433, has no findings. Its training survival is a median of 500/500 over iterations 950–999, against the unchanged 0.90 bar. Total steps over total endings gives a cross-check of 489.5, so the figure is not an artefact of the cap. The corrected verdict is `runs/w2-2/gait-adr433.json` in the project copy; the stored `review.json` was left as written [rec: mild-lily-4405].

- **Run `w2-2`** [rec: kind-loom-7489]. It was pre-registered (commit `1c4600e1`) as a warm start (`--init-from`) from `w2-1`'s policy on the byte-identical ADR-410 task bundle (`b0913fa0…`). Settings: 1000 × 2048, seed 0, `--timeout 10800`, `--stop-on-collapse`, grounding enforced, thresholds unchanged. The rollout went **1,443.8 mm forward over the full 10 s episode**. It never tipped, stayed upright 100% of the time, and was stepping. The first verdict was walked=false only because `training_survival` read iteration 999 (31.9 steps). That iteration is a horizon-boundary batch, where time-limit truncations count as endings. The verdict, curve and W1 video (153.9 s/300 s) are published (commit `4bfe59e1`) [rec: kind-loom-7489].
- **Run `w2-1`: walked = false, diagnosed** [rec: bold-reef-1724]. From scratch at 1000 × 2048, seed 0, on a local RTX 5090, with no tokens, it exited 0 in 2,241.7 s with no collapse. Reward/step rose from 1.16 to 2.62. Policy `d8b87d2e…` was verified to 1.2e-7 and declared at revision `f6d32a58…`. It tipped past 45° at 4.36 s (step 218/500) after 97.7 mm of travel with a −52° heading. Diagnosis: it learned to stand, because under the ADR-410 weights standing nets about +2/step and walking adds at most +1. The tip fell inside the 2–8 s disturbance window. Under ADR-433 its survival passes (median 487.6/500), but it **stays walked = false** [rec: mild-lily-4405]. Its W1 video is published [rec: calm-mesa-1063].
- Not run at ADR-433's revision: the full `cli/tests` and `pixi run test-engine`. Only `test_walk.py` and `test_ot10_contract.py` ran (93 passed). C1 still needs both suites at the final revision [rec: mild-lily-4405].

## Negative knowledge

- [scope: ADR-410 reward weights on ot10-quadruped-3, from scratch, 1000×2048, seed 0 | confidence: medium | evidence: bold-reef-1724, kind-loom-7489] Standing out-earns walking under these weights (about +2/step standing against at most +1 more for walking), and a from-scratch run of this size converged on standing. A second 1000-iteration warm start on the unchanged task did walk. That is one run of evidence each, not a general claim about the overlay.
- [scope: training survival read off a single trainer iteration | confidence: high | evidence: kind-loom-7489, mild-lily-4405] The trainer's episode length is `unroll*envs/endings`, with truncations counted. With unroll 20 and horizon 500, every 25th batch is a horizon boundary, and iteration 999 always is. A last-iteration read therefore fails healthy runs. ADR-433 reads a trailing-window median instead.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- bold-reef-1724 — W2 run w2-1: pre-registered, trained 1000×2048 on a copy of ot10-quadruped-3, walked=false, diagnosed
- calm-mesa-1063 — w2-1's W1 video published; rollout seed null; next is the pre-registered warm start
- kind-loom-7489 — W2 run w2-2: warm-started, 1.44 m forward upright, walked=false on a horizon-boundary survival artifact, diagnosed
- mild-lily-4405 — ADR-433 re-review: w2-2 walked=true, w2-1 still walked=false
