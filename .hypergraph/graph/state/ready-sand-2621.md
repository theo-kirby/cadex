---
node_id: cba79b00-c24d-5645-a748-33e794aa38d3
slug: ready-sand-2621
title: D7. A two-wheeled balancing robot goes through the lifecycle
created_at: '2026-09-13T21:25:10+00:00'
parents:
- round-sun-8398
summary: ''
---
Status: open

## Current

**Robin is accepted and visible on the persistent dashboard, but D7 remains open: restore fails and blocks training.** The complete product-agent-authored candidate was accepted at revision `71709063d6af7ee357d5bb5b409e3332730a1465e0caa62f92f93535ec04cd84` after an actor repair changed only reset lift from [1,3] to [3,5] mm. Acceptance retained 24 valid single solids (five printable, nineteen catalog), 276 measured BREP pairs, 84 passing fit checks and 139.60133 g. Pocket gaps are 0.30 mm and shaft/hub gap 0.05 mm; no design floor or grounded dynamics component, and joint residuals are zero. Receipts and limitations are under `docs/probes/ot6/robin/ACCEPTED.md`, `repair.json` and `fit.json` (ADR-337) [rec: salty-fox-4449].

The persistent server now serves accepted Robin: fresh browsers at 1400×900 and 400×850 show 24 components, 57,044 triangles, real solids by default and nine outlines under the labelled proxy toggle, with no horizontal overflow. A subsequent section request failed on restore digest mismatch (`806ab1343b7c...` versus `d7e568d29a53...`). Reproducibility must be repaired before training, recording and seed measurements; none of that lifecycle evidence exists yet [rec: salty-fox-4449].

Charter criterion: **D7. A two-wheeled balancing robot goes through the lifecycle.** The product agent designs it from a prompt in a fresh project (MG90S or another catalog motor, catalog wheels or modelled printable wheels, a body that mounts the board and battery volume), it meets D5's inventory and fit rules, trains once (bounded), and its videos and measurements are on the dashboard. The human owns the checkbox edit [rec: brisk-ledge-9638].

## Negative knowledge

- [scope: Robin recovery attempts before acceptance | confidence: high | evidence: wise-brook-4842, copper-haven-4303, northern-trail-4014] Initial reset-floor rejection left only the motor probe accepted. Complete-source recovery was provider-refused, including opus, sonnet and haiku selections; those attempts establish no future availability. The later literal repair and acceptance supersede the probe-only state, not the historical failures [rec: salty-fox-4449].
- [scope: accepted Robin revision 71709063d6af | confidence: high | evidence: salty-fox-4449] Retained dashboard geometry does not prove successful reopen. Wheel subelement ordering and small inertia differences were observed, but are not a proven diagnosis of the restore mismatch. Bay, boss-gap and engagement dimensions remain source-derived because section failed; wheel clearance does not verify press-fit or axial retention, and 0.3 mm motor shoulder clearance is not face registration. Measured screw/insert overlap is 4.852224 mm³ each, correcting the original stdout's 12.566 mm³. Reconcile judgement: retain declared `open` status while explicitly identifying broken reopen as the immediate training blocker.

## Provenance

- brisk-ledge-9638 — the ot6 directive (ADR-328) declared this criterion as gap `gap-d7-two-wheeled-balancing-robot`
- wise-brook-4842 — failed first Robin design attempt and probe-only acceptance
- copper-haven-4303 — recovered complete candidate; provider refused repair, so D9 fallback was taken
- northern-trail-4014 — three alternate model selections also provider-refused; Finch operator checks passed
- salty-fox-4449 — literal reset repair accepted, retained inventory and fits, live Robin dashboard, and restore mismatch blocking training
