---
node_id: 9cfd448a-7c63-5b21-b4e7-cb3ca42ce4c8
slug: staid-mountain-7730
title: 'ot11 C1: REPORT.md gains every evaluation, judge score, revision and failure, pinned to an evaluation ledger'
created_at: '2026-10-01T05:17:59+00:00'
parents:
- keen-walrus-1609
summary: ''
---
## What

`docs/probes/ot11/REPORT.md` now has four of C1's missing sections, each held to a receipt by `cli/tests/test_ot11_report.py`:

- **Every evaluation.** All 21 stored evaluations across the five ot11 projects. They come from `runner/eval_ledger.py`, a new collector that reads only each project's `evaluations/*/evaluation.json` and `retained/judge-*.json`, and writes `retained/ot11-evaluations.json`. Each evaluated policy is attributed to the run that trained it by hashing every policy file under a registered run. The two known negatives stay unattributed. The table lists verdict, seeds passed, failing seeds per predicate, terminations and film.
- **Every judge score.** All 12 blind-judge scores: w2-2, Robin, r2-confirm-1 and r3-confirm-1, on 3 seeds each. Each score is `claude-opus-5-5`, 3 calls, medians, against the bar of total ≥9 with no trait under 2.
- **Every revision the agent made, and why.** 14 rows. Each gives the change, the measurement it cites (from the run's own `registration.json` reason), the evaluation row that answered it, and whether it helped.
- **Every failure.** 17 of 21 evaluations failed, 2 of them void (r8). Two runs collapsed and seven hit their budget. r9-steelfoot was a refused start, not an attempt. The reach r3 warm-start refusals are listed. Three pipeline defects were found by the pipeline's own evaluations (ADR-465, 467, 468).

Tests added: each table equals its receipt row for row. Verdict equals the pass rule. Judge `meets_bar` is recomputed from the medians and the bar. Judge and spec agree on all 12 scores. Each revision row's evaluation was trained by that run, and its seeds-passed figure matches. The failure counts match both receipts. The receipt carries no machine path. A fixture test covers the collector: hash attribution, checkpoint preferred over `best`, an unregistered run left unattributed, row order, and judge-to-evaluation linking.

## Why

The critic's message said: if r10-steelfoot-fresh has finished, publish it; if it is still training, write REPORT.md's missing C1 sections from existing receipts, and do not rebuild under a live session. At 00:57 r10 was `running` (supervisor pid 1754562, trainer on the GPU, started 00:25 with a 2,400 s budget). The product agent's session 3 turn (pid 1623771) owns r10's evaluation. So this iteration took the critic's second branch, which serves C1.

Not done, and why: r10 is not published, because it was still training. r9 has no ledger row yet. Regenerating `ot11-runs.json` now would add r9 and a half-finished r10, so the report says r9's row will come with that regeneration, and it names r9 as a refused start in *Every failure*.

## Method

Read every retained receipt's shape and every project's `evaluations/` directory (21 directories in 5 projects). Wrote `eval_ledger.py`, mirroring `run_ledger.py`: reads only the stated inputs, keeps no machine path, and sorts by project order, then the start of the run that trained the policy, then write time. Write time alone put r6's ADR-467 re-read after r7. Generated the receipt with
`pixi run python docs/probes/ot11/runner/eval_ledger.py --out docs/probes/ot11/retained/ot11-evaluations.json --judges docs/probes/ot11/retained $P/ot11-w2-negative $P/ot11-robin-negative $P/ot11-robin-1 $P/ot11-heron-1 $P/ot11-quad-1`.

Rendered the two tables from the receipt. Wrote the revisions table from each run's registration reason, and corrected four "cited" cells against the reasons verbatim, for example r3's chatter, which was read from the knee-speed reward term and not from the film. Cross-checked the attribution against README: heron r1–r3 `best`, r4 `it 475`, r5 `it 400`, bal-1 `it 400`, r7 `it 200` and r8 `it 300` all match the per-round sections.

## Result

- `pixi run python -m pytest cli/tests/test_ot11_report.py`: 10 passed. Full `pixi run python -m pytest cli/tests -x`: **1 failed, 1220 passed, 1 skipped**. The failure is `test_walk.py::test_the_same_walk_handles_a_linear_carriage`, and rerun alone it fails the same way, with `jaxlib._jax.XlaRuntimeError: INTERNAL: cuSolver internal error`. The cause is the GPU, not this diff. The product agent's session 3 launched `r11-speedp…` at 01:12 (trainer pid 1893406, 24.7 of 32.6 GB), and that test runs JAX on the same GPU. This diff touches only `cli/tests/test_ot11_report.py`, `docs/probes/ot11/` and a new probe runner. The test was not rerun under the live job, per the one-GPU-job rule. **The next iteration must rerun it once the GPU is free.** Because `-x` stopped the suite at that test, the tests after it in collection order did not run in this pass. `pixi run test-engine` was not run, because no engine file changed.
- C1 now has receipts for every training run (14), every evaluation (21) and every judge score (12), plus the agent's revisions and the failures. Still missing from REPORT.md: **remaining defects**, and the final-revision suite results. Both belong at the close.
- r10-steelfoot-fresh **finished during this iteration**: `finished`, 800 iterations, policy `34f47b03…`. The product agent has since started an eleventh walk run, `r11-speedp…`, at 01:12, so session 3 is live and r10's evaluation is the agent's. Publish r10 (and later r11) from the agent's stored evaluation, then regenerate both receipts with `run_ledger.py` and `eval_ledger.py` (same project list). That adds r9 as a `failed`/refused row (decide whether the run table should mark refused starts separately, since the charter says a refused start is not an attempt) and adds r10 plus its evaluation. Then update the counts the tests pin: 14 runs, 21 evaluations, 17 failed, 14 revision rows. Those numbers are deliberately pinned so that a regeneration forces the prose to move with it.
- Before calling r10's evaluation valid, check HIP_MM and WEIGHT_N against the evaluation's `rig` (critic's instruction, carried forward).
- The 7 `train_start` errors in heron's session are cited from the receipt. README traces 5 of them to warm-start paths; the other 2 are not individually explained in any receipt.
- No new dependency. No engine, protocol or payload change.

Dispatch closed: 1 unit — REPORT.md's evaluation, judge-score, revision and failure sections, each pinned to a new receipt (`eval_ledger.py`).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 6c127c5684329b331d7f5b585b6a0f84c84b8152

## State Impact

- target: golden-bay-4173 — REPORT.md now lists all 21 stored evaluations and all 12 judge scores from retained/ot11-evaluations.json (runner/eval_ledger.py), the agent's 14 revisions with the measurement each cited and whether the next evaluation helped, and every failure; test-pinned. Remaining: remaining-defects section, final-revision suites, and regenerating both ledgers for r9 (refused), r10 (finished) and r11 (training).
