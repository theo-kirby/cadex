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

Charter criterion: **F3. Fit is checked across each joint's range.** For every joint with declared limits, the checker places the real solids at poses across that range at a declared step, holding the other joints at the solved pose, and reports per pair the minimum distance, the maximum common volume and the joint value of first contact. The agent can reach the result, and so can `cadex clearance --sweep`. Evidence: an engine test on a two-link fixture whose contact begins at a known angle, reported within one step; on a copy of `ot6-finch`, the knee-to-thigh contact reported with its angle; measured runtime per joint recorded, and a bound on it enforced. Declared target `gap-f3-fit-checked-across-each`; a record may say "ticks F3" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

The known target on Finch: fit was a solved-pose check only, and knee flexion past approximately 60° can bring the sole toward the thigh cheeks (`cool-hill-9617`). The ot6 projects are read-only; the sweep runs on a copy under the operator's cadex-projects directory. [rec: kind-dusk-1609]

Reconcile judgement: `open` — declared by the ot7 directive with no evidence yet; flips to `working` only when a record carries the criterion's evidence, on the reading ot5 and ot6 used (evidenced pending the owner's tick) [rec: kind-dusk-1609].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f3-fit-checked-across-each`
