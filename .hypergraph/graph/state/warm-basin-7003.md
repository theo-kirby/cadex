---
node_id: 9612e7d6-bbb4-5465-be9d-0e82ad49021d
slug: warm-basin-7003
title: A3. Appearance and design quality are declared and measured
created_at: '2026-09-27T15:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run ot10: **A3. Appearance and design quality are declared and measured.** It asks for per-part roles and a palette in xscript (documented in `docs/XSCRIPT.md`), carried into inventory, `render`, `look` and review. Review and `look` must report the proxies (hardware silhouette share, sharp printed outside-edge share, material count), and each proxy needs a crude-fails/designed-passes test [rec: damp-dusk-8045].

Every part now has evidence. The owner ticks the box; roles do not [rec: sweet-sage-3253].
- **Roles in xscript** (ADR-413, `b8d61de0`). Roles are declared per component and a palette per assembly. They are validated at declaration and absent from the digest when undeclared. Inventory, render, look and review's render block carry them [rec: fresh-orchard-6718]. `render.materials` resolves role → palette → inventory default (purchased → graphite, printed → bone) [rec: happy-garden-2470].
- **P1 and P3** (ADR-414, `bba15a47`). Measured on the hero with a 512 px depth pass against the frozen bars. They are reported by render, look and review.json. The measurement changes no pixel [rec: shy-clover-2326].
- **P2 `sharp_outside_edge_share`** (ADR-415, `fe21211a`, `b829f43e`). `cadex_part_worker.sharp_edge_facts` measures sharp convex edge length at the frozen 60°, with seams excluded. It is carried as the `sharp_edges` fact through inventory `source_facts`, summed over printed placements, and reported by `render.edge_proxy` in render, look and review. When a printed part has no measurement, P2 is `null` with a reason rather than a false zero. There are crude and designed fixtures on the real kernel (`test_part_sharp_edges.py`) and in the CLI (`test_look.py`) [rec: sweet-sage-3253]. P2 also reports `unresolved_edges` summed over printed placements, and the summary calls the share a lower bound when that count is nonzero (ADR-416) [rec: light-tower-4418].
- **P2 leaves out world geometry** (ADR-424). The components the fit reports as world geometry (the floor) are excluded — the same set P1 and `look` already exclude. `inventory.printed_edges` keeps per-placement figures under `by_component`; `render.edge_proxy(inventory, environment)` names the excluded set under `left_out_as_environment`; `write_render` and the bridge's `look` pass it. Threshold, rubric, bar, procedure and `contract.json` unchanged. Pinned by `test_sharp_outside_edge_share_leaves_out_the_floor` (fails on the prior source). Motivation: a floor slab could dilute or inflate the share — hexapod-4's filleted floor hid its link edges, and quadruped-3's agent rounded its floor to lower P2 from inside a turn [rec: amber-flame-4976] [rec: humble-lily-1303].
- **Verification.** The packaged lifecycle gate gave 23 passed on the staged payload, which also settles the gate ADR-413 owed [rec: sweet-sage-3253]. At ADR-424: cli 1005 passed / 1 skipped, engine 2237 passed / 53 skipped; no engine or payload change [rec: amber-flame-4976].
- **hex3 baseline:** P1 0.373 (fails ≤ 0.20), **P2 0.189** (passes ≤ 0.25 after ADR-424; was 0.332 with its 500×400×3 floor's 3,612 mm of sharp edge counted), P3 2 (meets 2–3). hex3 still fails P1 and the judged bar (2/21); P2 does not see hex3's T4 0 because its thin plates' long faces dominate the edge length — P2 is necessary, not sufficient [rec: shy-clover-2326] [rec: sweet-sage-3253] [rec: amber-flame-4976].

## Negative knowledge

- [scope: hex3's accepted revision | confidence: high | evidence: shy-clover-2326] hex3 fails P1: 37% of its hero silhouette (76,170 of 204,356 subsamples) is bought servos and boards.
- [scope: hex3's accepted revision | confidence: high | evidence: amber-flame-4976] P2 does not catch hex3's flat-plate form (T4 0): with the floor left out it passes at 0.189. A low sharp-edge share is not evidence of designed form.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- happy-garden-2470 — role/palette hook in render.materials
- fresh-orchard-6718 — xscript appearance roles and palette, carried through (ADR-413)
- shy-clover-2326 — P1/P3 measured and reported (ADR-414)
- sweet-sage-3253 — P2 measured and reported (ADR-415), packaged gate 23 passed, hex3 P2 0.332; A3 evidence complete
- light-tower-4418 — P2 unresolved_edges surfaced and the lower-bound wording added (ADR-416)
- amber-flame-4976 — ADR-424: P2 leaves out world geometry; hex3 P2 re-measured 0.189 (passes), fails P1 not P2
- humble-lily-1303 — quadruped-3's agent rounded its floor to dilute P2 in-turn, the dilution ADR-424 removes
