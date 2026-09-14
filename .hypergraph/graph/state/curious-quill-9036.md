---
node_id: 18a6f1a6-c0c6-55d8-bca2-3925cebfd6ad
slug: curious-quill-9036
title: F3. Fit is checked across each joint's range
created_at: '2026-09-14T17:28:05+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

**The product publishes opt-in, bounded exact-solid sweeps for limited rigid-tree hinges (ADR-349).** `assembly.assembly(..., sweep_step_degrees=5)` produces `clearance_sweep` before simulation moves components. Fresh sandbox-inheriting FreeCAD subprocesses move copied descendant BREPs from solved connector frames, preserving other joint coordinates and parent placements. Each pair reports minimum distance, maximum common volume and first sampled contact in degrees; reports include timings, limits and explicit incomplete coverage. Acceptance remains advisory [rec: misty-spark-6372].

Endpoint-inclusive samples use at most the declared step, capped at 73 poses and 2,000 pairs per joint. Native-query budgets are 90 seconds per joint and 180 seconds per assembly; serialization/cleanup add overhead and the enclosing script timeout still applies. Each joint verifies solved-pose agreement within 0.0001 mm and 0.001 mm³. Unsupported or unavailable geometry, non-hinge limited joints, flexible/closed/coupled/static-joint graphs, unsolved assemblies and exhausted budgets report incomplete; unlimited joints are outside coverage. The suite-integrated sphere fixture reports first contact at 79° against an analytic 78.522°, within its 1° step; published results and accepted identity survive restart in the staged payload [rec: misty-spark-6372].

The earlier read-only experiment on an unchanged accepted Finch copy validated all 406 solved pairs and independent MJCF poses. Four 5° hinge sweeps took 19.642–57.919 sweep seconds (24.935–63.142 whole-child seconds), each below the experiment's 180-second per-joint bound. Both knees retained a sampled 1 mm shin-to-thigh gap, zero common volume and no first contact. This experiment is distinct from the product producer, which has not yet been requested on Finch [rec: amber-lantern-9712] [rec: misty-spark-6372].

Charter criterion: **F3. Fit is checked across each joint's range.** For every joint with declared limits, the checker places the real solids at poses across that range at a declared step, holding the other joints at the solved pose, and reports per pair the minimum distance, the maximum common volume and the joint value of first contact. The agent can reach the result, and so can `cadex clearance --sweep`. Evidence: an engine test on a two-link fixture whose contact begins at a known angle, reported within one step; on a copy of `ot6-finch`, the knee-to-thigh contact reported with its angle; measured runtime per joint recorded, and a bound on it enforced. Declared target `gap-f3-fit-checked-across-each`; a record may say "ticks F3" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

Reconcile judgement: retain `open`. Agent inspection and `cadex clearance --sweep` cannot yet read the product result, product Finch measurement is outstanding, and other limited joints remain incomplete. The charter's predicted Finch contact is contradicted at sampled poses, so it is not carried as an established fact [rec: amber-lantern-9712] [rec: misty-spark-6372].

## Negative knowledge

- [scope: accepted Finch sampled hinge experiment | confidence: high | evidence: amber-lantern-9712] Accepted Finch revision `b6862234556355f799591f314cde6b1a7caadb7d4659a0051d18a442c098912f`, four independent hinges at 5° steps. Confidence: high for sampled poses only. Neither knee contacts the thigh over sampled 0–90°; no newly overlapping pair appears, while 12 pre-existing overlapping thread-engagement pairs remain. This is neither passing F2 fit nor proof against between-sample contact. The predicted contact past about 60° is unsupported on this revision [rec: amber-lantern-9712].
- [scope: producer prototype after FreeCAD initialization | confidence: high | evidence: misty-spark-6372] Confidence: observed failure in this unit. A fork-only child stalled on a native futex; the shipped producer uses a fresh executable instead [rec: misty-spark-6372].

## Provenance

- kind-dusk-1609 — ot7 directive declared the F3 criterion and predicted Finch contact
- amber-lantern-9712 — bounded read-only exact-solid experiment, independent pose witness and negative Finch result
- misty-spark-6372 — product producer, known-angle/budget/restoration tests and remaining coverage/exposure gaps
