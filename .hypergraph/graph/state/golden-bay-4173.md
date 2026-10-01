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

**Every section C1 names exists in REPORT.md and both suites plus the packaged gate are green at the latest engine change; it stays open because R1's walk session 5 is still running and the report must move with it, and the final revision is not yet reached** [rec: civic-key-7068] [rec: early-bramble-6327].

- **Every training run.** `docs/probes/ot11/REPORT.md` lists **21 runs, 20 attempts, 34,588.52 s** supervised GPU time (walk 15 / 29,240.54 s), with `r16-alive10` training and not yet in the ledger [rec: early-bramble-6327]. `runner/run_ledger.py` builds `retained/ot11-runs.json` from each project's `registration.json` and `training-status.json`, machine paths stripped; a trainer that exits `failed` before its first iteration is kept with `attempt: false` (r9-steelfoot), and a live run is listed under `in_progress` (test-pinned) [rec: shady-pond-5657] [rec: gilded-ridge-5195]. Supervised time throughout; round 5's README section quotes trainer time (1,898 s), noted on the page [rec: gilded-ridge-5195].
- **Every evaluation and judge score.** `runner/eval_ledger.py` reads only each project's `evaluations/*/evaluation.json` and `retained/judge-*.json` and writes `retained/ot11-evaluations.json`: **27 evaluations** (23 failed; 4 void, the last at row 26) [rec: early-bramble-6327] [rec: true-tree-5366], **12 judge scores** (w2-2, Robin, r2-confirm-1, r3-confirm-1 × 3 seeds; `claude-opus-5-5`, 3 calls, medians, bar total ≥ 9 with no trait under 2; judge and spec agree on all 12). Each evaluated policy is attributed to its run by hashing every policy file under a registered run; the two known negatives stay unattributed [rec: staid-mountain-7730].
- **Every revision and every failure.** The agent's revisions table gives the change, the measurement it cites from the run's `registration.json`, the evaluation that answered it and whether it helped; rows through `r15-stiffspring-clearfoot` (20 revision rows) [rec: staid-mountain-7730] [rec: true-tree-5366] [rec: early-bramble-6327]. Failure counts moved with each round (20 of 24 at round 11) [rec: rapid-peak-4236]; failures include two collapses, budget hits, r9's refused start, reach r3 warm-start refusals, and three pipeline defects found by the pipeline's own evaluations (ADR-465, 467, 468) [rec: staid-mountain-7730] [rec: terse-bramble-7437].
- **Remaining defects.** Written and test-pinned (`test_ot11_report.py::test_remaining_defects_cite_receipts_that_exist`; each item cites a receipt or ADR that must exist): R1 0/10 on rows 13–27; no walking gait judged; the judge's stepping/slip blind spot (ADR-460/461/463); rounds 1–3 on the pre-ADR-465 trainer; the spec-block mechanism-rule check is the actor's, not the product's [rec: forest-stone-4700]. "W10 under a gait unmeasured" became **measured failing** at round 11 [rec: rapid-peak-4236]; round 12 adds **the foot contact margin hole** (nothing in the product refuses a margin that lifts a foot out of what the frozen predicates read), pinned by a test against the r13 receipt [rec: autumn-current-6021]; ADR-470 now makes the product void it, and REPORT.md's margin and gate bullets say so [rec: civic-key-7068]. The rebuilt-model contact line cites row 27's W10 [rec: early-bramble-6327].
- **Pinned.** `cli/tests/test_ot11_report.py` holds every table to its receipt row for row, recomputes verdicts and judge `meets_bar`, checks revision rows against the runs that trained them, and pins the counts so a regeneration forces the prose to move [rec: staid-mountain-7730] [rec: autumn-current-6021]. Its seed invariant is `passed + failed == seeds and void <= failed`, since a product-voided seed is also a failed one [rec: true-tree-5366].
- **Suites.** `pixi run test-engine` **2,523 passed, 60 skipped** at the ADR-470 revision; no engine source has changed since [rec: civic-key-7068] [rec: early-bramble-6327]. `pixi run python -m pytest cli/tests` **1,271 passed, 1 skipped at `01789834`**, run CPU-only (`CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`) so it never shared the GPU with r16 [rec: early-bramble-6327]. An intervening GPU run at `208623d6` failed `test_walk.py::test_the_same_walk_handles_a_linear_carriage` on cuSolver contention with r15 — a GPU collision, superseded by the CPU run [rec: true-tree-5366].
- **Packaged lifecycle gate.** Paid for ADR-469 and ADR-470: `test_cadexd_lifecycle.py` **23 passed, 0 skipped** on a payload staged from each [rec: civic-key-7068]. Owed again only after a later engine or payload change.

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
