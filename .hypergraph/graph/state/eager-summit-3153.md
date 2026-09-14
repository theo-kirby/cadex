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

**Every F3 unit so far has green engine, CLI and staged-payload gates, each after a fresh build and stage.** Latest, against commit `7fb47e51` and re-run in the following iteration: `pixi run test-engine` 2,127 passed/53 skipped (346.72 s); `pixi run python -m pytest cli/tests` 641 passed/1 skipped (566.76 s), run to completion; packaged lifecycle 18 passed (16.59 s; the slider parametrisation is the eighteenth). The ADR-350 consumer unit before it: engine 2,124/53 skipped, CLI 641/1 skipped, packaged 17. Iteration 12's own CLI run had been killed at turn end and is not claimed; iteration 13 found the installed engine one comment line behind the committed worker and rebuilt before gating [rec: green-river-3790] [rec: curious-cedar-4881] [rec: kind-flint-2780] [rec: misty-spark-6372].

F2 previously passed engine 2,117/53 skipped and packaged lifecycle 16, but its full CLI run had 636 passed/1 skipped/1 failed at the unchanged review-lifecycle telemetry assertion (15 history points followed by iteration 18, expecting 19 points). An isolated retry passed. Separate changing-telemetry reads suggest a timing race, not proof of a pre-existing failure; no dashboard source or test was edited. Three later green full CLI runs supply passing observations without erasing that retained failure [rec: crisp-ember-0302] [rec: misty-spark-6372] [rec: green-river-3790] [rec: curious-cedar-4881].

Charter criterion: **F9. Nothing regressed.** Both suites green; the packaged gate green for any engine protocol or payload change. The retained ot6 designs (copies of Finch, Robin and Heron) still open, and the product checker's failing set on each matches what the ot6 probe checkers found, with every difference explained. Declared target `gap-f9-nothing-regressed-both-suites`; a record may say "ticks F9" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

The retained-design baseline remains the ot6 probe checkers at `docs/probes/ot6/{finch,heron}/fit_check.py` and Robin's fit receipts, applied to copies of read-only ot6 projects. A Finch copy has opened and rebuilt under the product checker (F3's product measurement) and its sweep first-contact set was compared with the static failing set, but that is not the failing-set comparison against the ot6 probe checker this criterion asks for [rec: kind-dusk-1609] [rec: kind-flint-2780].

Reconcile judgement: retain `open`. Suite and payload gates are repeatedly green, but the reopen-and-failing-set comparison for Finch, Robin and Heron against the ot6 probe checkers, with every difference explained, is still not done [rec: kind-flint-2780] [rec: curious-cedar-4881].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f9-nothing-regressed-both-suites`
- happy-dawn-1960 — initial F1 suite results, focused licensing repair and packaged-gate scope
- steady-quartz-9854 — corrected CLI suite 636 passed/1 skipped; explicitly no fresh engine or F9 claim
- crisp-ember-0302 — F2 engine/packaged success, retained full-CLI telemetry failure and passing isolated retry
- misty-spark-6372 — fresh green engine/CLI/packaged producer runs; retained-design comparisons remain open
- green-river-3790 — ADR-350 consumer unit: engine 2,124/53, CLI 641/1, packaged 17 after one build and stage
- curious-cedar-4881 — ADR-351 backfill with iteration-13 gates: engine 2,127/53, CLI 641/1 to completion, packaged 18
- kind-flint-2780 — same green gates reaffirmed; Finch copy rebuilt under the product checker; retained-design comparison still open
