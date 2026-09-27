---
node_id: 9612e7d6-bbb4-5465-be9d-0e82ad49021d
slug: warm-basin-7003
title: A3. Appearance and design quality are declared and measured
created_at: '2026-09-27T15:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Charter criterion for run ot10: **A3. Appearance and design quality are declared and measured.** It asks for per-part roles and a palette in xscript (documented in `docs/XSCRIPT.md`), carried into inventory, `render`, `look` and review. Review and `look` must report the proxies (hardware silhouette share, sharp printed outside-edge share, material count), and each proxy needs a crude-fails/designed-passes test [rec: damp-dusk-8045].

Landed:
- **Roles in xscript** (ADR-413, `b8d61de0`). Roles are declared per component and a palette per assembly. They are validated at declaration and absent from the digest when undeclared. Inventory, render, look and review's render block carry them. Suites: 2212 passed / 53 skipped (engine), 980 passed / 1 skipped (cli) [rec: fresh-orchard-6718]. `render.materials` resolves role → palette → inventory default (purchased → graphite, printed → bone) [rec: happy-garden-2470].
- **P1 and P3** (ADR-414, `bba15a47`). Measured on the hero with a 512 px depth pass against the frozen bars. They are reported by render, look and review.json via the render block. **hex3: P1 0.373 (fails ≤ 0.20), P3 2 (meets)**. The measurement changes no pixel. cli suite net 986 passed / 1 skipped after fixing `test_walk`'s note pin [rec: shy-clover-2326].

Open:
- **P2 `sharp_outside_edge_share` is not measured.** The planned route is a worker fact (sharp convex edge length / total edge length per printed solid), carried in inventory rows [rec: shy-clover-2326].
- **The packaged lifecycle gate is owed for ADR-413's engine change** and has not been run; the P2 unit should run it [rec: fresh-orchard-6718] [rec: shy-clover-2326].

## Negative knowledge

- [scope: hex3's accepted revision | confidence: high | evidence: shy-clover-2326] hex3 fails P1: 37% of its hero silhouette (76,170 of 204,356 subsamples) is bought servos and boards.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- happy-garden-2470 — role/palette hook in render.materials
- fresh-orchard-6718 — xscript appearance roles and palette, carried through (ADR-413)
- shy-clover-2326 — P1/P3 measured and reported; P2 and packaged gate open (ADR-414)
