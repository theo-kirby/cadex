---
node_id: 07285db2-b997-5129-9a6c-181697a82113
slug: swift-dusk-2951
title: The walk holds on a second mechanism
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Charter criterion: **The walk holds on a second mechanism.** The same entry point, with no code change specific to the mechanism, takes a second mechanism through the whole loop, and both projects' `PROGRESS.md` carry comparable numbers. Declared target `gap-walk-holds-second-mechanism-same` [rec: empty-wolf-3962]. The nt3 operator directive re-seeds the criterion unticked and says of it: "nt2 left the second-mechanism walk close to done (`sage-peak-2689`: the linear carriage ran through the same entry point with no dispatch change, and both projects carry comparable baseline numbers); finish and evidence it rather than restarting it" [rec: modest-summit-8554].

The unchanged `cadex walk` entry point trains, declares and verifies an ideal vertical slider/force-motor carriage beside a fresh revolute/torque-motor hinged-arm baseline, with no mechanism-specific workaround. Both repository-owned projects carry source, architecture/decision/sensor docs and comparable `PROGRESS.md` definitions and measurements; ADR-203 and reproduction commands record the qualification. Both verified rollouts reach 50 steps at 50 Hz with seed 3. Arm/carriage rollout totals are -27.1093842209/-24159.1953563, rollout means -0.542187684419/-483.183907126; walks take 15.22/13.52 s with sampled process-tree RSS below 1 GB. The full real-engine/trainer CLI suite passes 138 tests without skips [rec: sage-peak-2689].

Reconcile judgement: flipped from `working` to `open` on the operator's directive, which re-seeds the criterion unticked and asks for it to be finished and evidenced rather than restarted [rec: modest-summit-8554]. The nt2 evidence stands. What is missing is derivable from the charter and the sibling gaps: the "whole loop" the criterion names starts at design, and the walk does not yet complete from `--prompt` on any mechanism [rec: misty-rain-9048, on `crisp-reef-5607`]; the second-mechanism qualification was from an installed example recipe, as the baseline was. The node returns to `working` when the human ticks the criterion or a record verifiably closes it.

## Negative knowledge

- [scope: one-iteration linear-carriage qualification | confidence: high | evidence: sage-peak-2689] Working-level evidence denotes pipeline qualification, not control quality or hardware validation: the carriage falls to origin z=-4699.378313 mm at 1 s on an ideal unlimited guide. Torque and force costs use different units, so these rewards do not rank designs. Only source, docs and numbers are versioned in the parent repository; policy assets, checkpoints, traces and accepted caches remain untracked.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- sage-peak-2689 — second mechanism qualifies through the unchanged walk with baseline metrics and real CLI tests; control quality remains poor
- modest-summit-8554 — nt3 operator directive re-seeds the criterion unticked: finish and evidence it rather than restarting it
