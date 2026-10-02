---
node_id: d595bc9c-2371-54e0-b5f8-bd55c3092882
slug: misty-star-3641
title: 'ot11 C1: closing report has a receipt row per criterion; suites green at 4d2baa7d; done claimed for critic review'
created_at: '2026-10-01T19:28:52+00:00'
parents:
- eager-bloom-9137
summary: ''
---
## What
C1 work toward the closing report (commit after `4d2baa7d`):
- `docs/probes/ot11/REPORT.md` gains **"Every criterion and its receipt"**: one row each for P1–P4, R1–R3 and C1, naming the ADRs and linking the retained receipts (contract, known-negative measurements and judge scores, P2 evaluations, R2's held-out targets, P4 rounds, the three confirmations' registrations, evaluations and judge scores, the two ledgers).
- New test `test_every_criterion_has_a_receipt_that_exists` in `cli/tests/test_ot11_report.py`: all eight criteria present, every link a file, every ADR cited exists, no placeholder left. 14 of 14 report tests pass.
- Suites at the confirmation revision `4d2baa7d`: `pixi run test-engine` **2529 passed, 61 skipped**; `cli/tests` CPU-only (`CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`) **1288 passed, 1 skipped** (`test_review_server.py:851`, needs `CADEX_REVIEW_HOST`). No failures.
- Packaged gate not rerun: no engine source changed since ADR-470's restage (only `training/` and one cadex_tests file in ADR-471), when it passed 23 of 23.

## Why
The critic's named unit: C1 (golden-bay-4173) — run both suites, finish REPORT.md with a receipt per criterion keeping the remaining defects (W2's thin tilt margin stays in), export and check, claim done without ticking. Deviation: the critic also asked to "fold the open records" and reconcile; this dispatch forbids the reconcile skill in a work iteration, so I did not, and say so here. The fix-first record for R1 confirmation 1 is `eager-bloom-9137`.

## Method
Read REPORT.md's sections and README.md's three confirmation sections; checked every cited file exists and ADR-470 is the last engine-source change (`git log 6ff24621..HEAD -- src/Mod/cadex package`). Ran both suites in parallel, CPU-only for cli/tests per the one-GPU-job rule.

## Result
**Done is claimed for critic review.** P1–P4, R1–R3 and C1 each have evidence and a receipt row in REPORT.md; no owner box is ticked. Remaining defects stay in REPORT.md: W2's tilt margin (23.9–24.2° of 30 on four seeds), the judge's blind spot on stepping/slip, W10 on the old steel-ball rounds, margin-read predicates, ADR-465's early rounds, no in-product refusal of a reworded predicate.
- Handoff (critic asked for one): what I tried this run — closing C1 by evidence rows rather than new measurement. Next: a reconcile pass must fold rapid-pond-0713, eager-bloom-9137 and this node (tail is three, a reconcile is due); then, if the critic accepts done twice, the run stops; otherwise the long-term rung (a fourth behaviour through the same loop, e.g. a gripper) with no new code path.
- The plan's short bet (rollout-pose clearance) was banned by the critic; it is not touched.

Dispatch closed: 1 unit — C1 closing report gets per-criterion receipts; both suites green; done claimed for critic review

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 2c1588a75c3f243f86caed2023a45e4ebb81d46f

## State Impact

- target: golden-bay-4173 — REPORT.md carries 'Every criterion and its receipt' (P1-P4, R1-R3, C1), test-pinned; at 4d2baa7d test-engine 2529 passed / 61 skipped and cli/tests CPU-only 1288 passed / 1 skipped; packaged gate last 23/23 after ADR-470 with no engine source change since; done claimed for critic review, owner boxes unticked
