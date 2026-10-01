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

**Every section C1 names exists in REPORT.md and both suites plus the packaged gate are green at the latest engine change; it stays open because R1 is unmet (walk session 7 closed at 6 of 10, no session 8 registered), the report must move with any later round, and the final revision is not yet reached** [rec: civic-key-7068] [rec: humble-canyon-4360].

- **Every training run.** `docs/probes/ot11/REPORT.md` lists **29 runs, 27 attempts (2 refused), 48,098.03 s** GPU time through `r22-gentle-contact25`, none in progress [rec: humble-canyon-4360]; at r21b it was 28 runs / 26 attempts / 46,370.91 s [rec: southern-rain-8433]. `runner/run_ledger.py` builds `retained/ot11-runs.json` from each project's `registration.json` and `training-status.json`, machine paths stripped; a trainer that exits `failed` before its first iteration is kept with `attempt: false` (r9-steelfoot), and a live run is listed under `in_progress` (test-pinned) [rec: shady-pond-5657] [rec: gilded-ridge-5195]. Supervised time throughout; round 5's README section quotes trainer time (1,898 s), noted on the page [rec: gilded-ridge-5195].
- **Every evaluation and judge score.** `runner/eval_ledger.py` reads only each project's `evaluations/*/evaluation.json` and `retained/judge-*.json` and writes `retained/ot11-evaluations.json`: **34 evaluations** (4 void, the last at row 26) [rec: humble-canyon-4360] [rec: true-tree-5366]; row 31's `written_at` moved when session 7's agent re-evaluated r19 under the same key, every other number unchanged [rec: deep-moss-5363]; **12 judge scores** (w2-2, Robin, r2-confirm-1, r3-confirm-1 × 3 seeds; `claude-opus-5-5`, 3 calls, medians, bar total ≥ 9 with no trait under 2; judge and spec agree on all 12). Each evaluated policy is attributed to its run by hashing every policy file under a registered run; the two known negatives stay unattributed [rec: staid-mountain-7730].
- **Every revision and every failure.** The agent's revisions table gives the change, the measurement it cites from the run's `registration.json`, the evaluation that answered it and whether it helped; rows through `r22-gentle-contact25` (r21b and r22 each added one) [rec: staid-mountain-7730] [rec: southern-rain-8433] [rec: humble-canyon-4360]. Session 6's lost third run (driver counted a re-evaluation), r21's refused start, and r21b's and r22's failures are recorded under *Every failure*; the session-7 driver note is corrected (all three of its runs trained in one turn, so the driver's limit did not stop it after r21b) [rec: brisk-ember-6734] [rec: deep-moss-5363] [rec: forest-rose-3078] [rec: humble-canyon-4360]. Failure counts moved with each round (20 of 24 at round 11) [rec: rapid-peak-4236]; failures include two collapses, budget hits, r9's refused start, reach r3 warm-start refusals, and three pipeline defects found by the pipeline's own evaluations (ADR-465, 467, 468) [rec: staid-mountain-7730] [rec: terse-bramble-7437].
- **Remaining defects.** Written and test-pinned (`test_ot11_report.py::test_remaining_defects_cite_receipts_that_exist`; each item cites a receipt or ADR that must exist): R1 never 10/10 on rows 13–34 (best 9/10 at row 31) [rec: brisk-ember-6734] [rec: humble-canyon-4360]; no walking gait judged; the judge's stepping/slip blind spot (ADR-460/461/463); rounds 1–3 on the pre-ADR-465 trainer; the spec-block mechanism-rule check is the actor's, not the product's [rec: forest-stone-4700]. "W10 under a gait unmeasured" became **measured failing** at round 11 [rec: rapid-peak-4236]; round 12 adds **the foot contact margin hole** (nothing in the product refuses a margin that lifts a foot out of what the frozen predicates read), pinned by a test against the r13 receipt [rec: autumn-current-6021]; ADR-470 now makes the product void it, and REPORT.md's margin and gate bullets say so [rec: civic-key-7068]. The W10 line now cites row 29's sustained-stepping measurement [rec: weathered-river-6058].
- **Pinned.** `cli/tests/test_ot11_report.py` holds every table to its receipt row for row, recomputes verdicts and judge `meets_bar`, checks revision rows against the runs that trained them, and pins the counts so a regeneration forces the prose to move [rec: staid-mountain-7730] [rec: autumn-current-6021]. Its seed invariant is `passed + failed == seeds and void <= failed`, since a product-voided seed is also a failed one [rec: true-tree-5366].
- **Suites.** `pixi run test-engine` **2,529 passed, 61 skipped** on the ADR-471 tree (2,523/60 at ADR-470; ADR-471 adds trainer tests only, no engine source) [rec: civic-key-7068] [rec: misty-grove-2592] [rec: humble-canyon-4360]. `pixi run python -m pytest cli/tests` **1,273 passed, 1 skipped** at `f7d131d4`, `0d4ae72f` and `6babb356` (1,272/1 at `dccb2382`), run CPU-only (`CUDA_VISIBLE_DEVICES=""`) so it never shared the GPU with a training round [rec: civic-bluff-7621] [rec: deep-moss-5363] [rec: forest-rose-3078] [rec: southern-rain-8433] [rec: humble-canyon-4360]. `test_ot11_rounds.py` gained `test_a_re_evaluation_does_not_use_up_a_round` and `test_a_refused_start_does_not_use_up_a_round` with the driver fixes [rec: scarlet-cove-2359] [rec: forest-rose-3078]. An intervening GPU run at `208623d6` failed `test_walk.py::test_the_same_walk_handles_a_linear_carriage` on cuSolver contention with r15 — a GPU collision, superseded by the CPU run [rec: true-tree-5366].
- **Packaged lifecycle gate.** Paid for ADR-469 and ADR-470: `test_cadexd_lifecycle.py` **23 passed, 0 skipped** on a payload staged from each [rec: civic-key-7068]. Owed again only after a later engine or payload change; ADR-471 changed neither [rec: misty-grove-2592].

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
- civic-key-7068 — lifecycle gate 23/23 for ADR-469 and ADR-470; test-engine 2523/60, cli/tests 1271/1; REPORT.md margin and gate bullets updated
- true-tree-5366 — ledgers at 20 runs / 26 evaluations (4 void); report seed invariant corrected for product-voided seeds; cli/tests broken by GPU contention
- early-bramble-6327 — ledgers at 21 runs / 27 evaluations; cli/tests 1271/1 on CPU at 01789834
- civic-bluff-7621 — ledgers at 22 runs / 28 evaluations; cli/tests 1271/1 on CPU at bc088ea5
- weathered-river-6058 — ledgers at 23 runs / 29 evaluations; cli/tests 1271/1 on CPU at b3bcdeb7
- round-crane-1720 — ledgers at 24 runs (40,325.52 s) / 30 evaluations / 23 revisions; cli/tests 1271/1 on CPU
- brisk-ember-6734 — ledgers at 25 runs (42,335.79 s) / 31 evaluations; cli/tests 1271/1 on CPU at 69f75709
- scarlet-cove-2359 — rounds.py stop-rule test added with the driver fix
- deep-moss-5363 — ledgers at 27 runs (25 attempts, 2 refused, 44,301.93 s) / 32 evaluations / 25 revisions; cli/tests 1272/1 on CPU at dccb2382
- forest-rose-3078 — rounds.py refused-start test added; cli/tests 1273/1 on CPU
- southern-rain-8433 — ledgers at 28 runs (26 attempts, 46,370.91 s) / 33 evaluations; cli/tests 1273/1 on CPU
- misty-grove-2592 — ADR-471 trainer-only change: test-engine 2529/61; no payload change, lifecycle gate not owed
- humble-canyon-4360 — ledgers at 29 runs (27 attempts, 48,098.03 s, none in progress) / 34 evaluations; session-7 driver note corrected; cli/tests 1273/1 on CPU
