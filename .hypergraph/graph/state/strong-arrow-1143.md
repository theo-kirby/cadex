---
node_id: ffe23c03-bc65-5617-a249-ac6648041dc8
slug: strong-arrow-1143
title: B4. Changes remain mechanically and causally reviewable.
created_at: '2026-09-22T17:39:47+00:00'
parents:
- open-cabin-5892
summary: ''
---
Status: working

## Current

**B4. Changes remain mechanically and causally reviewable.** The final accepted design has zero failing static fit checks, complete passing swept fit for both wheel joints, and a component inventory with catalog provenance. Compare it with the frozen baseline. Every mechanical, task or reward change comes from a product-agent turn on an ot9 project and has a before/after measurement. No actor design edit, grounded base, added stabilizer, hidden joint, shorter episode or weaker tilt/fall threshold may satisfy B3. [rec: curious-branch-9704]

**Measured on the final accepted revision ae889a9b, digest 078ebe87 [rec: long-glacier-5252].** Static fit passes: 0 failing of 378 pairs, 0 intersections. Swept fit is complete and passing for exactly both wheel axles (±1800° in 100° steps, 0 mm³ common volume; its 0.050 mm minimum is the hub-bore running clearance declared as fit intent, identical in the baseline). All 25 fixed-joint attachments touch. Inventory: 28 components, 23 catalogued with cited sources, `derived_catalog_sources` empty. Receipt: commit 0c021f24, `docs/probes/ot9/retained/r5-robin-fit.json`, pinned by `cli/tests/test_ot9_contact_compression.py` [rec: long-glacier-5252].

**Unchanged against the ot8 baseline [rec: long-glacier-5252].** Clearance, fit and inventory equal ot8's `evidence/g4-resolve/before/` once revision and timing are removed; the MJCF is byte-identical (933b1ac6), so mass and actuator limits are too; the script differs only in the policy literals and the parameters only in `policy_on` and `rollout_seed`. There was no mechanical, task or reward change in ot9, so the product-agent-turn clause holds trivially rather than as an achievement [rec: long-glacier-5252].

**Contact compression, reported apart from intersections [rec: long-glacier-5252].** Wheel spheres touch the floor at 0.000 mm in the solved keyframe; settled compression under the policy is 0.578-0.582 mm on all ten seeds (ot8's hold: 0.576 mm), with 1.83-2.30 mm peaks only at the 3-5 mm reset landing. Read by `docs/probes/ot9/runner/contact_compression.py` [rec: long-glacier-5252].

*Reconcile judgement*: the declared evidence for B4 is complete; status `working`, not complete, because only the owner ticks the checkbox [rec: long-glacier-5252].

## Negative knowledge

None yet.

## Provenance

- curious-branch-9704 — the criterion as the ot9 charter declares it
- long-glacier-5252 — final design measured, equal to the ot8 baseline; compression reported apart
