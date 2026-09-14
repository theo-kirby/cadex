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

**F1's regression evidence is partial for F9.** The initial F1 CLI suite passed 634 tests with one skip. Its engine run had 2,114 passed, 53 skipped and one failure: the frozen-prompt test lacked an SPDX header. The header was fixed and the focused licensing suite then passed 10 tests with one skip; no clean full-engine rerun is claimed. The packaged gate was not run because no protocol or payload changed [rec: happy-dawn-1960]. The subsequent CLI-only complete-list correction passed 636 tests with one skip; it reran neither the engine suite nor the packaged gate and makes no F9 claim [rec: steady-quartz-9854].

Charter criterion: **F9. Nothing regressed.** Both suites green; the packaged gate green for any engine protocol or payload change. The retained ot6 designs (copies of Finch, Robin and Heron) still open, and the product checker's failing set on each matches what the ot6 probe checkers found, with every difference explained. Declared target `gap-f9-nothing-regressed-both-suites`; a record may say "ticks F9" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

The ot6 floor to hold: `pixi run test-engine` 2,114 passed / 53 skipped and the CLI suite 610 passed / 1 skipped at ot6's close (`civic-lily-1239`), since raised by the owner's ADR-342–344 tests. The ot6 probe checkers are `docs/probes/ot6/{finch,heron}/fit_check.py` and Robin's fit receipts; their failing sets are the reference the product checker is compared against on copies of the read-only ot6 projects. Pre-existing gate failures are reported against the baseline, not hidden. [rec: kind-dusk-1609]

Reconcile judgement: retain `open`; the records do not establish a clean full-engine rerun or the retained ot6 reopen and failing-set comparison required by F9 [rec: happy-dawn-1960] [rec: steady-quartz-9854].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f9-nothing-regressed-both-suites`
- happy-dawn-1960 — initial F1 suite results, focused licensing repair and packaged-gate scope
- steady-quartz-9854 — corrected CLI suite 636 passed/1 skipped; explicitly no fresh engine or F9 claim
