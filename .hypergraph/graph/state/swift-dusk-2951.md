---
node_id: 07285db2-b997-5129-9a6c-181697a82113
slug: swift-dusk-2951
title: The walk holds on a second mechanism
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

The unchanged `cadex walk` entry point trains, declares and verifies an ideal vertical slider/force-motor carriage beside a fresh revolute/torque-motor hinged-arm baseline, with no mechanism-specific workaround. Both repository-owned projects carry source, architecture/decision/sensor docs and comparable `PROGRESS.md` definitions and measurements; ADR-203 and reproduction commands record the qualification. [rec: sage-peak-2689]

Both verified rollouts reach 50 steps at 50 Hz with seed 3. Arm/carriage rollout totals are -27.1093842209/-24159.1953563, and rollout means are -0.542187684419/-483.183907126; training-batch means are separately labelled -0.380198150873/-82.3199081421. Walks take 15.22/13.52 s with sampled process-tree RSS below 1 GB. The full real-engine/trainer CLI suite passes 138 tests without skips, including slider walk and arm iterate coverage. [rec: sage-peak-2689]

## Negative knowledge

- [scope: one-iteration linear-carriage qualification | confidence: high | evidence: sage-peak-2689] Working denotes pipeline qualification, not control quality or hardware validation: the carriage falls to origin z=-4699.378313 mm at 1 s on an ideal unlimited guide. Torque and force costs use different units, so these rewards do not rank designs. Only source, docs and numbers are versioned in the parent repository; policy assets, checkpoints, traces and accepted caches remain untracked.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- sage-peak-2689 — second mechanism qualifies through the unchanged walk with baseline metrics and real CLI tests; control quality remains poor
