---
node_id: 5ade230b-7376-5fc7-8385-b340262f5567
slug: spring-glade-6801
title: A6. A design is presented, not screenshotted
created_at: '2026-09-27T15:18:35+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run ot10: **A6. A design is presented, not screenshotted.** `cadex review` leads each project with its studio hero and a concept sheet (hero, orthographic line views, palette, name, and mass, servo count and size); the sheet is also one PNG in the project's review directory; `docs/REVIEW-DESIGN.md` changes in the same commit; the A5 designs' sheets are committed at 300 KB or less each [rec: damp-dusk-8045].

Evidence reported complete, pending the owner's tick [rec: hidden-tooth-3627] (ADR-430, commit `0f7747c6`):

- `cadex render` writes `review/render/sheet.png`, 1536×1024. The left half is the 1024 px studio hero, identical pixel for pixel to `hero.png`. The right half has the name, the revision, mass, servo count, size, a swatch per appearance role used, `front`/`right`/`top` line views and the A1 proxies. Mass is the sum of the accepted MJCF's inertials; servos are the inventory's `servo` family; size is the drawn extent; an unreadable number prints `N/A` with a reason. It adds no new dependency. [rec: hidden-tooth-3627]
- `/api/project` carries a read-only `presentation` block. `/presentation/{sheet,hero}.png` serves only what that block offers. The review stage opens once on a new first **Concept** tab. `docs/REVIEW-DESIGN.md` §14 (plus §2, §12) changed with the page. [rec: hidden-tooth-3627]
- `cli/tests/test_sheet.py` (10 tests) pins shape and size limit, identity, numbers, refusals and routes. A browser test at both charter sizes pins that the page leads with the sheet. cli suite 1028 passed, 1 skipped; engine suite 2242 passed, 53 skipped. [rec: hidden-tooth-3627]
- Committed sheets, drawn from `/tmp` copies: ot10-biped-1 138 KB (0.389 kg, 6 servos); ot10-quadruped-3 210 KB (0.479 kg, 8); ot10-hexapod-10 212 KB (0.654 kg, 12). All are under the 300 KB cap. [rec: hidden-tooth-3627]

The human owns the charter checkbox; roles report results and do not tick it. Maintainer judgement: status flipped to `working` on complete reported evidence, as with A1–A3. [rec: hidden-tooth-3627]

## Negative knowledge

- [scope: A6 concept sheet line views | confidence: high | evidence: hidden-tooth-3627] The line views are image-space drawings of the tessellation: silhouette, object boundaries and creases over 35° only. There is no hidden-line removal and there are no dimensions. View labels use the product's axis names, so a +X-facing biped shows its visor in `right`.
- [scope: A6 evidence | confidence: high | evidence: hidden-tooth-3627] Two gaps remain. The sheets have not been viewed on the operator URL, and the page has no side-by-side comparison of designs.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- hidden-tooth-3627 — ADR-430 concept sheet in `cadex render`; review leads with it; three A5 sheets committed
