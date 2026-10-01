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

**Most of the closing report exists; remaining defects and the final-revision gates do not** [rec: staid-mountain-7730] [rec: terse-bramble-7437].

- **Every training run.** `docs/probes/ot11/REPORT.md` lists **17 runs, 16 attempts, 25,968.49 s** supervised GPU time, none in progress, through walk round 10 (`r11-speedpay`); walk is 11 runs / 20,620.51 s [rec: terse-bramble-7437]. `runner/run_ledger.py` builds `retained/ot11-runs.json` from each project's `registration.json` and `training-status.json`, machine paths stripped; a trainer that exits `failed` before its first iteration is kept with `attempt: false` (r9-steelfoot), and a run whose supervisor has not ended is listed under `in_progress` and in no total (test-pinned) [rec: shady-pond-5657] [rec: gilded-ridge-5195]. The ledger uses supervised time throughout; round 5's README section quotes trainer time (1,898 s), noted on the page [rec: gilded-ridge-5195].
- **Every evaluation and judge score.** `runner/eval_ledger.py` reads only each project's `evaluations/*/evaluation.json` and `retained/judge-*.json` and writes `retained/ot11-evaluations.json`: **23 evaluations, 12 judge scores** (w2-2, Robin, r2-confirm-1, r3-confirm-1 × 3 seeds; `claude-opus-5-5`, 3 calls, medians, bar total ≥ 9 with no trait under 2; judge and spec agree on all 12). Each evaluated policy is attributed to its run by hashing every policy file under a registered run; the two known negatives stay unattributed [rec: staid-mountain-7730] [rec: terse-bramble-7437].
- **Every revision and every failure.** The agent's revisions table (14 rows at its creation, plus r10 and r11) gives the change, the measurement it cites from the run's `registration.json`, the evaluation that answered it and whether it helped. Failures: **19 of 23** evaluations failed (2 void, r8); two runs collapsed and seven hit their budget (as of 21 evaluations); r9 a refused start, not an attempt; reach r3 warm-start refusals; three pipeline defects found by the pipeline's own evaluations (ADR-465, 467, 468); a session-3 failure bullet [rec: staid-mountain-7730] [rec: terse-bramble-7437].
- **Pinned.** `cli/tests/test_ot11_report.py` holds every table to its receipt row for row, recomputes verdicts and judge `meets_bar`, checks revision rows against the runs that trained them, and pins the counts (17 runs / 23 evaluations / 16 attempts / 19 failed) so a regeneration forces the prose to move [rec: staid-mountain-7730] [rec: terse-bramble-7437].
- **Not yet written**: the remaining-defects section, and the final-revision suite results [rec: staid-mountain-7730].
- **Suites.** Full `cli/tests` with the GPU free, no `-x`: **1,268 passed, 1 skipped**, exit 0, 1,117 s (2026-10-01, `shady-pond-5657`'s revision; the skip needs `CADEX_REVIEW_HOST`); round 10 changed no product code [rec: shady-pond-5657] [rec: terse-bramble-7437]. Last `pixi run test-engine`: 2,521 passed, 60 skipped at `d410b098` [rec: keen-walrus-1609]. ADR-467 changed `CadexEvaluation.py` and ADR-468 `CadexDynamics.py`, but `build/release` and the staged payload have not been rebuilt since, so the packaged lifecycle gate is still owed at the final revision [rec: pale-ember-2389].

## Negative knowledge

None yet.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
- gilded-ridge-5195 — REPORT.md's run ledger started (12 runs, 17,963.36 s), test-pinned to retained/ot11-runs.json
- happy-cliff-3687 — run ledger at 13 runs / 19,684.20 s; cli/tests 1260 passed, 1 skipped
- pale-ember-2389 — engine suite 2,510 passed after ADR-467; payload not rebuilt since
- rough-bell-4381 — run ledger at 14 runs / 21,692.35 s (row 14)
- keen-walrus-1609 — suites at d410b098: engine 2,521 passed, cli 1,261 passed; r9/r10 not yet in the ledger
- staid-mountain-7730 — REPORT.md gains every evaluation (21), judge score (12), revision (14) and failure, pinned to eval_ledger.py's receipt
- shady-pond-5657 — run_ledger marks refused starts attempt:false and live runs in_progress; 16 runs / 22 evaluations; full cli/tests 1268 passed, 1 skipped with the GPU free
- terse-bramble-7437 — ledgers at 17 runs / 16 attempts / 25,968.49 s and 23 evaluations, none in progress; REPORT.md and its test moved with them
