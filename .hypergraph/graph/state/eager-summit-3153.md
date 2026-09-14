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

**The F3 producer unit has green engine, CLI and staged-payload gates.** `pixi run test-engine`: 2,121 passed/53 skipped; CLI: 637 passed/1 skipped; packaged lifecycle: 17 passed, including sweep publication/restoration. Engine build and staging succeeded. Final focused sweep tests passed 2 tests, including additional closed-graph and pair-cap coverage [rec: misty-spark-6372].

F2 previously passed engine 2,117/53 skipped and packaged lifecycle 16, but its full CLI run had 636 passed/1 skipped/1 failed at the unchanged review-lifecycle telemetry assertion (15 history points followed by iteration 18, expecting 19 points). An isolated retry passed. Separate changing-telemetry reads suggest a timing race, not proof of a pre-existing failure; no dashboard source or test was edited. The later green full CLI run supplies a new passing observation without erasing that retained failure [rec: crisp-ember-0302] [rec: misty-spark-6372].

Charter criterion: **F9. Nothing regressed.** Both suites green; the packaged gate green for any engine protocol or payload change. The retained ot6 designs (copies of Finch, Robin and Heron) still open, and the product checker's failing set on each matches what the ot6 probe checkers found, with every difference explained. Declared target `gap-f9-nothing-regressed-both-suites`; a record may say "ticks F9" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

The retained-design baseline remains the ot6 probe checkers at `docs/probes/ot6/{finch,heron}/fit_check.py` and Robin's fit receipts, applied to copies of read-only ot6 projects [rec: kind-dusk-1609].

Reconcile judgement: retain `open`. Green suites and a shipped-payload gate are now evidenced, but reopen and failing-set comparisons for all three retained designs, with every difference explained, remain outstanding [rec: misty-spark-6372].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f9-nothing-regressed-both-suites`
- happy-dawn-1960 — initial F1 suite results, focused licensing repair and packaged-gate scope
- steady-quartz-9854 — corrected CLI suite 636 passed/1 skipped; explicitly no fresh engine or F9 claim
- crisp-ember-0302 — F2 engine/packaged success, retained full-CLI telemetry failure and passing isolated retry
- misty-spark-6372 — fresh green engine/CLI/packaged producer runs; retained-design comparisons remain open
