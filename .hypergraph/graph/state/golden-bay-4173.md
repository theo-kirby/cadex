---
node_id: 8ce02322-9b58-568d-80ee-efb9ba389abb
slug: golden-bay-4173
title: C1. Regressions and a closing report are complete (ot11)
created_at: '2026-09-30T07:04:58+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot11: **C1. Regressions and a closing report are complete.** - Both full suites pass at the final revision, plus the packaged lifecycle gate for any engine or payload change. - `docs/probes/ot11/REPORT.md` lists every training run with its settings, its budget and the GPU time spent, and every evaluation and judge score. It also covers every revision the agent made and why, every failure, and the remaining defects. - Reconcile, then claim done for critic review without ticking the owner boxes. [rec: kind-spire-3578]

Declared target: `gap-c1-regressions-closing-report-complete`. This node tracks the criterion as a gap; it becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: kind-spire-3578]. Reconcile judgement: ot10's criterion of the same name is a separate state node (`southern-prairie-3683`, working); this run's C1 names a different report and different gates, so it is tracked as its own node and the title carries the run.

**Started: the closing report's run ledger exists; the rest of C1 does not** [rec: gilded-ridge-5195] [rec: happy-cliff-3687] [rec: rough-bell-4381].

- `docs/probes/ot11/REPORT.md` lists every ot11 training run with its settings, budget and supervised GPU time: **14 runs, 21,692.35 s** through walk round 8 (`r8-stance`, row 14); `cli/tests/test_ot11_report.py` counts 14 [rec: rough-bell-4381]. Before it: 13 runs, 19,684.20 s (balance 900.57 s, reach 4,447.41 s, walk 7 runs 14,336.22 s) [rec: happy-cliff-3687]. `r9-steelfoot` (refused at start, 52 s) and `r10-steelfoot-fresh` are not yet in it [rec: keen-walrus-1609]. `runner/run_ledger.py` builds `retained/ot11-runs.json` from each project's `registration.json` and `training-status.json`, machine paths stripped; `cli/tests/test_ot11_report.py` holds the page to it row for row (it fails on a one-cent change). Re-run the collector and add a row for each new run [rec: gilded-ridge-5195] [rec: happy-cliff-3687].
- The ledger uses supervised time throughout; round 5's README section quotes trainer time (1,898 s), noted on the page [rec: gilded-ridge-5195].
- **Not yet written**: the evaluations and judge scores, the revisions the agent made and why, the failures and the remaining defects sections [rec: gilded-ridge-5195].
- **Suites at `d410b098`** (ADR-468): `pixi run test-engine` 2,521 passed, 60 skipped; `cli/tests` 1,261 passed, 1 skipped [rec: keen-walrus-1609]. ADR-467 changed `CadexEvaluation.py` and ADR-468 `CadexDynamics.py`, but `build/release` and the staged payload have not been rebuilt since, so the packaged lifecycle gate is still owed at the final revision [rec: pale-ember-2389].

## Negative knowledge

None yet.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
- gilded-ridge-5195 — REPORT.md's run ledger started (12 runs, 17,963.36 s), test-pinned to retained/ot11-runs.json
- happy-cliff-3687 — run ledger at 13 runs / 19,684.20 s; cli/tests 1260 passed, 1 skipped
- pale-ember-2389 — engine suite 2,510 passed after ADR-467; payload not rebuilt since
- rough-bell-4381 — run ledger at 14 runs / 21,692.35 s (row 14)
- keen-walrus-1609 — suites at d410b098: engine 2,521 passed, cli 1,261 passed; r9/r10 not yet in the ledger
