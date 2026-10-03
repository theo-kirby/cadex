---
node_id: 0d1755fd-e113-53fb-9393-31d06b2ce68d
slug: shady-clover-5534
title: W1. Nothing the product could do headlessly was lost (orun2)
created_at: '2026-10-03T10:54:47+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run orun2: **W1. Nothing the product could do headlessly was lost.** - On a copy of an existing robot project, the whole walk runs and every step is visible in the dashboard: 1. prompt; 2. accepted design; 3. params sweep; 4. `look` and render; 5. STEP/STL export; 6. MJCF export; 7. a short training run on the 5090; 8. `evaluate`. - Both full suites pass, and so does the packaged lifecycle gate. - The CLI and dashboard have no feature the shell parity ledger below marks "ported" without a test. - **The parity ledger is complete:** `docs/SHELL-PARITY.md` gives each of these one row: - every `mesh_agent` module; - each of its 23 tools; - each of the seven Cadex editors. Each row says one of three things: **ported** (where, and the test), **already covered** (where), or **dropped** (why, and the ADR). No row is blank. [rec: winter-stone-5109]

**Parity ledger skeleton exists (commit `94b5be8f`).** `docs/SHELL-PARITY.md` has one row for each of the 47 `mesh_agent` entries (44 Python modules + `pi_tools.js`, ~29.6k lines, all read in full by read-only readers, nothing copied), each of the 23 shell tools and each of the 7 Cadex editors — no row blank. Statuses are still interim (*to port* / *drop proposed*): no row yet carries a final ported-with-test or dropped-with-ADR verdict, and none of the walk legs has been run against the dashboard. Reconcile judgement: stays `open` — a skeleton is not measured evidence for the criterion [rec: old-arrow-4088].

Declared target: `gap-w1-nothing-product-could-do`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: earlier runs have criteria with the same letters, so every orun2 gap title carries the run. Flip to working only when the criterion has measured evidence; it stays open until then [rec: winter-stone-5109].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- old-arrow-4088 — SHELL-PARITY.md skeleton: 47 module / 23 tool / 7 editor rows, none blank, statuses interim
