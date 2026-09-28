---
node_id: 63e28d9b-bd64-5b6b-9865-fe2d74d69094
slug: old-cabin-6515
title: 'ot10: closing report brought to HEAD — A5 clause stated, ADR-434/435, suites green; done claimed for review'
created_at: '2026-09-28T23:13:08+00:00'
parents:
- sharp-tide-2612
summary: ''
---
## What
Brought ot10's closing report (`docs/probes/ot10/REPORT.md`) up to the last counted turn and the last change. The report now:
- lists ADR-434 and ADR-435;
- states plainly what A5's "one failing design fails" clause means for the ten misses;
- has fresh full-suite and packaged-gate receipts at HEAD.

This claims done for critic review. No owner box is ticked. Commits `eaef9f93` and `d75664fc`.

## Why
The critic's message: close out rather than add more tooling. Update the report with every attempt and score and with ADR-434/435, state what the clause means, run both suites at HEAD, and claim done. That serves C1 (`first-snow-5587`'s ot10 counterpart; the charter's C1) and finishes A5's publication (`loyal-fountain-8709`).

**Deviation, stated:** the critic also asked for a reconcile first (fold `tidy-banner-2442` and `sharp-tide-2612`). This iteration's dispatch forbids the hypergraph-reconcile skill, `hypergraph update` and state edits in a work iteration, "no exceptions". I followed the dispatch and did not reconcile. The tail is now three unreconciled records (with this one), which meets the charter's reconcile trigger. The next iteration should be the housekeeping reconcile pass, if the loop grants one.

A correction to the critic's premise, which the report now states: the pre-registered confirmation round was `ot10-hexapod-11` (meets), `ot10-quadruped-4` (meets) and `ot10-biped-2` (misses at 2). So it was 2 of 3, not 3 of 3. `ot10-biped-3` was a separate pre-registration made after ADR-434.

## Method
- Rewrote the A5 verdict section around the clause:
  - Sixteen counted turns, ten misses: hexapods 1–8, quadruped 2 and biped 2.
  - Any one miss fails A5, and a later pass does not reverse it. Nothing is re-scored or retired.
  - The highest bar reached is six designs that meet the bar across all three body plans.
- Added one sentence on ADR-435 to the summary. Added remaining defect 10: the build-reply overflow, 85,954 → 12,163 characters, amends ADR-346, no counted turn behind it.
- Added a final regressions table at `c758db3a` plus this edit.
- The attempts table was already correct and test-held, so it is unchanged.

## Result
- `cli/tests/test_ot10_report.py` + `test_ot10_contract.py`: 45 passed on the edited page.
- `pixi run test-engine -rs`: 2,247 passed, 53 skipped, 0 failed (395 s). The skips fall into the four documented causes: 47 JAX/MJX offboard (ADR-084), 5 Blender recipe executable, 1 `CADEX_ENGINE_ROOT` packaged test.
- `pytest cli/tests -rs`: 1,068 passed, 1 skipped (`CADEX_REVIEW_HOST`), 0 failed (782 s).
- Packaged lifecycle gate (`CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64`): 23 passed. No engine or package file changed since ADR-434's commit `45636b04`.
- A5 is **not met by its letter** (ten counted misses), and the report says so. Six designs meet the bar across all three body plans. W2 `walked = true` on `w2-2`.
- **Done is claimed for critic review.** The owner ticks the boxes. Nothing here re-scores anything, and no rubric, bar, judge or prompt changed.
- Concern: three unreconciled records (`tidy-banner-2442`, `sharp-tide-2612`, this one). Reconcile is due. The critic's accepted fold targets are `chilly-union-8972` and `loyal-fountain-8709`.

Dispatch closed: 1 unit — ot10 closing report updated with every A5 attempt, ADR-434/435 and the plain meaning of "one failing design fails"; both suites and the packaged gate green at HEAD; done claimed for critic review

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: d75664fcbfd9cec276ffc4a0945c903229b562ca

## State Impact

- target: loyal-fountain-8709 — The closing report (docs/probes/ot10/REPORT.md, commits eaef9f93, d75664fc) now states A5's clause plainly: 16 counted turns, 10 misses (hexapods 1-8, quadruped 2, biped 2), each failing A5 on its own; the confirmation round was 2 of 3 and ot10-biped-3 a separate pre-registration; six designs meet the bar across all three body plans. At HEAD engine 2247 passed/53 skipped, CLI 1068/1 skipped, packaged gate 23 passed; done claimed for critic review, owner boxes unticked
