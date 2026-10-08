---
node_id: 36d712fb-42d9-52d9-980b-d7bc4fe886ef
slug: loyal-mesa-6439
title: 'ADR-599: smoke payloads, contact allowance, driven loop probe; refused script kept'
created_at: '2026-10-08T06:53:19+00:00'
parents:
- placid-lodge-9970
summary: ''
---
## What
Three of orun5's four leftover defects fixed (ADR-599): smoke treats a free body in a grounded rig as a payload; smoke's exact-solid check allows a pair in simulated contact its contact depth (volume ≤ depth × A/2, within --penetration-mm); smoke drives position actuators through a 2 s sine when a model has loop closures, so a driven loop that opens at a coarse step fails and names the step; a refused `cadex script --set` keeps the source at review/script.rejected.py and says whether script.py was reverted.

## Why
orun5 REPORT §10 items 4, 5 and 7: the rebuilt ball-plate failed smoke on support and on a 7.5 µm contact; a driven loop at the 2 ms default sat 0.02–0.70 mm open unwarned; an agent lost an in-place edit twice, costing one training run.

## Method
cli/cadex_cli/smoke_runner.py (payloads, touches → smoke-contacts.json, driven probe), smoke.py and smoke_geometry.py (contact allowance), __main__.py (`_keep_rejected_source`). Tests in cli/tests/test_smoke.py, test_smoke_geometry_bound.py, test_commands.py. The live four-bar fixture's mjcf now sets solver_step_s=0.0005; at the default it fails 0.17 mm of the driven sweep.

## Result
Engine suite 2681 passed / 61 skipped; CLI suite 1229 passed / 1 skipped (GPU hidden). Still open: evaluations draw no tracker noise (ADR-588); seeding it changes the engine rollout the trainer witness is checked against.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 607b6cfe61eb4c3dc52362f52b4c7db594dd037f

## State Impact

- target: salty-isle-4063 — cadex smoke owes a free payload no floor, allows a simulated contact its depth, and drives a held loop so a coarse step fails (ADR-599)
