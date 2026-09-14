---
node_id: 15b58a5b-3a9d-5b54-bae4-f830d662bc95
slug: dusty-otter-7562
title: D6. The real biped trains, is measured and is recorded in the new look
created_at: '2026-09-13T21:25:10+00:00'
parents:
- round-sun-8398
summary: ''
---
Status: working

## Current

**D6's evidence list is complete pending the owner's tick (ADR-336).** Finch's stand task declares 400 steps at 50 Hz, a fall below 84.0 mm pelvis height, seeds 0–9 and reset variation on `pelvis_link` (task revision `a3dc4e9a0f84…`). The bounded GPU run `finch1` completed 240 PPO updates on 1024 environments in 2048.7 s, exit 0, with host peak 9.72 GB and GPU peak 15 695 MiB under `MemoryMax=20G` and a 3600 s timeout. Checkpoint 20 fell on 10/10 seeds at 0.20–0.34 s; the final policy stood the full 8 s on 10/10 and shuffled +361.1 mm mean (319–433). Checkpoint and final videos show real tessellation in `cadex-prototype-dark-v1` on the persistent dashboard, which selects `finch1-final` on a fresh visit at accepted revision `b68622345563…`. Evidence: `docs/probes/ot6/finch/training.json` and its receipt regression; full CLI suite 557 passed, 1 skipped [rec: tiny-tooth-8197].

The engine prerequisite is resolved (ADR-335): nothing grounded means a free base, with the first component held for solving and a free joint plus `environment/floor` in MJCF. Finch was re-accepted ungrounded at `bcce40a82d57…`; stock MuJoCo held it standing for 2 s and a 0.3 m/s shove made it fall onto, never through, the environment floor. No world geometry enters the design [rec: loyal-canyon-4623].

**The owner ticked D6 on 2026-09-14 with the evidence unchanged**, as worded and knowing the gaps the next charter (ADR-341) raises the bar on rather than re-running; there is no policy training in ot7 [rec: nimble-wing-3050].

Charter criterion: **D6. The real biped trains, is measured and is recorded in the new look.** One bounded real GPU training run on the redesigned biped, a checkpoint video and a final video in the D3 look on the operator dashboard, and the measured displacement, survival and falls over a declared episode and seed set. Standing for the full episode is the bar the report measures against; failing it is a valid measured result. Declared target `gap-d6-real-biped-trains-measured`; the human owns the checkbox edit [rec: brisk-ledge-9638].

Reconcile judgement: fold the prerequisite and subsequent evidence together as `blocked` → `working`; the later handoff satisfies the task, bounded training, measurement and video items the prerequisite record left owed. The human still owns the checkbox [rec: loyal-canyon-4623] [rec: tiny-tooth-8197].

## Negative knowledge

- [scope: Finch finch1 evidence | confidence: high | evidence: tiny-tooth-8197] The +361.1 mm shuffle is stand-task behaviour, not a walking result. The trainer's final running episode estimate (211/400 steps) and ten CLI rollouts (400/400) are distinct measurements. The checkpoint video was rendered manually after the driver's old triangle cap refused it. No run record preceded finch1: `preserved_records: {}` proves no earlier-record preservation; the receipt and README now say so.

## Provenance

- brisk-ledge-9638 — the ot6 directive declared D6
- sleepy-rain-9945 — the original static-base prerequisite
- loyal-canyon-4623 — ADR-335 resolves the free-base solve/export prerequisite and verifies Finch on the environment floor
- tiny-tooth-8197 — ADR-336 training and video evidence, ten-seed measurements, full CLI verification and corrected preservation claim
- nimble-wing-3050 — the owner ticked D6 on 2026-09-14; evidence unchanged
