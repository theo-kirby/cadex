---
node_id: f2d3bc57-743b-5295-8114-e65854ed2df7
slug: eager-summit-3153
title: F9. Nothing regressed
created_at: '2026-09-14T17:28:05+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

Charter criterion: **F9. Nothing regressed.** Both suites green; the packaged gate green for any engine protocol or payload change. The retained ot6 designs (copies of Finch, Robin and Heron) still open, and the product checker's failing set on each matches what the ot6 probe checkers found, with every difference explained. Declared target `gap-f9-nothing-regressed-both-suites`; a record may say "ticks F9" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

The ot6 floor to hold: `pixi run test-engine` 2,114 passed / 53 skipped and the CLI suite 610 passed / 1 skipped at ot6's close (`civic-lily-1239`), since raised by the owner's ADR-342–344 tests. The ot6 probe checkers are `docs/probes/ot6/{finch,heron}/fit_check.py` and Robin's fit receipts; their failing sets are the reference the product checker is compared against on copies of the read-only ot6 projects. Pre-existing gate failures are reported against the baseline, not hidden. [rec: kind-dusk-1609]

Reconcile judgement: `open` — declared by the ot7 directive with no evidence yet; flips to `working` only when a record carries the criterion's evidence, on the reading ot5 and ot6 used (evidenced pending the owner's tick) [rec: kind-dusk-1609].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f9-nothing-regressed-both-suites`
