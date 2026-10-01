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

**Every section C1 names now exists in REPORT.md and the gates are green at `87674b30`; it stays open because R1's walk session 4 is still running and the report must move with it, and the final revision is not yet reached** [rec: forest-stone-4700] [rec: autumn-current-6021].

- **Every training run.** `docs/probes/ot11/REPORT.md` lists **19 runs, 18 attempts, 30,313.69 s** supervised GPU time, with `r14-margin15-lift` in progress (in no total) [rec: autumn-current-6021]. `runner/run_ledger.py` builds `retained/ot11-runs.json` from each project's `registration.json` and `training-status.json`, machine paths stripped; a trainer that exits `failed` before its first iteration is kept with `attempt: false` (r9-steelfoot), and a live run is listed under `in_progress` (test-pinned) [rec: shady-pond-5657] [rec: gilded-ridge-5195]. Supervised time throughout; round 5's README section quotes trainer time (1,898 s), noted on the page [rec: gilded-ridge-5195].
- **Every evaluation and judge score.** `runner/eval_ledger.py` reads only each project's `evaluations/*/evaluation.json` and `retained/judge-*.json` and writes `retained/ot11-evaluations.json`: **25 evaluations** [rec: autumn-current-6021], **12 judge scores** (w2-2, Robin, r2-confirm-1, r3-confirm-1 × 3 seeds; `claude-opus-5-5`, 3 calls, medians, bar total ≥ 9 with no trait under 2; judge and spec agree on all 12). Each evaluated policy is attributed to its run by hashing every policy file under a registered run; the two known negatives stay unattributed [rec: staid-mountain-7730].
- **Every revision and every failure.** The agent's revisions table gives the change, the measurement it cites from the run's `registration.json`, the evaluation that answered it and whether it helped; rows through `r13-hovercost-margin` [rec: staid-mountain-7730] [rec: rapid-peak-4236] [rec: autumn-current-6021]. Failure counts moved with each round (20 of 24 at round 11) [rec: rapid-peak-4236]; failures include two collapses, budget hits, r9's refused start, reach r3 warm-start refusals, and three pipeline defects found by the pipeline's own evaluations (ADR-465, 467, 468) [rec: staid-mountain-7730] [rec: terse-bramble-7437].
- **Remaining defects.** Written and test-pinned (`test_ot11_report.py::test_remaining_defects_cite_receipts_that_exist`; each item cites a receipt or ADR that must exist): R1 0/10 on rows 13–25; no walking gait judged; the judge's stepping/slip blind spot (ADR-460/461/463); rounds 1–3 on the pre-ADR-465 trainer; the spec-block mechanism-rule check is the actor's, not the product's [rec: forest-stone-4700]. "W10 under a gait unmeasured" became **measured failing** at round 11 [rec: rapid-peak-4236]; round 12 adds **the foot contact margin hole** (nothing in the product refuses a margin that lifts a foot out of what the frozen predicates read), pinned by a test against the r13 receipt [rec: autumn-current-6021].
- **Pinned.** `cli/tests/test_ot11_report.py` holds every table to its receipt row for row, recomputes verdicts and judge `meets_bar`, checks revision rows against the runs that trained them, and pins the counts so a regeneration forces the prose to move [rec: staid-mountain-7730] [rec: autumn-current-6021].
- **Suites at `87674b30`.** `pixi run test-engine`: **2,521 passed, 60 skipped**; `pixi run python -m pytest cli/tests`: **1,270 passed, 1 skipped** (1,234.86 s), which includes `test_walk.py`'s tail owed since forest-stone-4700 (it had failed on cuSolver contention with r12 and not run under `-x`). The run shared the machine with r14 on the GPU; the skip was not identified (earlier runs attribute it to `CADEX_REVIEW_HOST`) [rec: autumn-current-6021] [rec: forest-stone-4700] [rec: shady-pond-5657].
- **Packaged lifecycle gate.** Paid: payload staged from current engine source (`build-engine` + `stage-engine`), `test_cadexd_lifecycle.py` **23 passed, 0 skipped**; engine source unchanged since `d410b098` (ADR-468). Owed again only after a later engine or payload change; rounds 11–12 changed none [rec: forest-stone-4700] [rec: autumn-current-6021].

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
- forest-stone-4700 — REPORT.md remaining-defects section written and test-pinned; packaged lifecycle gate 23/23 on a freshly staged payload; cli/tests test_walk tail unverified (GPU contention)
- rapid-peak-4236 — ledgers at 18 runs / 24 evaluations; W10-under-gait defect measured failing; test_walk tail still owed
- autumn-current-6021 — ledgers at 19 runs / 25 evaluations; foot-margin defect pinned; test-engine 2521/60 and cli/tests 1270/1 at 87674b30 pay the test_walk tail
