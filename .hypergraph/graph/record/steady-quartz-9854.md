---
node_id: 4c4a0e83-ca54-5bfc-860a-417474bce38d
slug: steady-quartz-9854
title: 'F1 correction: all failing pairs reach the reply; f2bf2c83 verified by the full CLI suite'
created_at: '2026-09-14T18:15:49+00:00'
parents:
- happy-dawn-1960
summary: ''
---
## What

Completed verification and recovered the missing causal record for commit `f2bf2c8364873ab50b57ccd68ef491409d5b1c92` (iteration 4), the F1 reply-completeness correction to ADR-346. Build replies now include every failing measured pair, including pairs beyond forty, with each name, distance and common volume. The forty-pair slice, limit constant and `failing_truncated` field are removed. `docs/CLI.md` and ADR-346 describe the complete list.

## Why

The critic explicitly required the full CLI suite and a causal record for `f2bf2c83` targeting F1 (`wild-horizon-5461`) before further work. This dispatch finishes that existing correction as its one unit; it does not begin F2 or reconciliation. The earlier parent record's bounded-to-forty Method statement and its unqualified F1 completion claim were premature: a scope pointer did not meet the charter's requirement for every failing pair in the reply. The correction fixes that defect. This record follows `happy-dawn-1960`, whose F1 implementation introduced it.

## Method

Reviewed the committed correction and its fixtures against the parent record. `test_fit_summary_names_every_failing_pair_however_many_there_are` uses ninety measured pairs, sixty failing, and asserts every failing name, distance and volume in measurement order. `test_a_build_reply_names_every_failing_pair_past_forty` checks the actual model-facing bridge reply for sixty failures among sixty-three pairs, including the stored ToolCall fit and count summary. Both assert no truncation field or redirect note. The critic's supplied evidence says both fixtures fail on the old code and 52 focused tests pass; those are prior critic results, not experiments repeated in this dispatch.

Ran `pixi run python -m pytest cli/tests` against unchanged HEAD `f2bf2c8364873ab50b57ccd68ef491409d5b1c92`, waited for completion, and captured its exit code and final summary. No product-agent design was run or edited. No new dependency, build, engine-source, protocol, payload, shell or dashboard change was made; the packaged gate and engine suite were not rerun for this CLI-only correction. The prior record's engine-suite failure followed by a focused licensing pass remains its historical evidence, not a fresh full-engine green claim.

## Result

Full CLI verification: **636 passed, 1 skipped in 515.14 seconds (0:08:35), exit 0**. This includes the two complete-list fixtures and the existing misleading-stdout real-engine transaction fixture. F1's forty-pair defect is corrected and now has full CLI verification and a causal record. No failure was observed in this run; this does not claim F9 or evidence for static intent, swept ranges or unassisted repairs.

The unreconciled tail becomes three records. The critic requests reconciliation next, then F2 fit-intent declarations and known Heron defect fixtures rather than the stale plan. This work dispatch explicitly forbids reconciliation and state/view writes, so none were performed; the runner must supply a permitted reconcile dispatch. No scope deviation from the critic's fix-first request and no new dependency. Graph export/check are the closing validation for this record before commit.

Dispatch closed: 1 unit — verify and causally record the F1 complete-failing-pair reply correction in f2bf2c83.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: f2bf2c8364873ab50b57ccd68ef491409d5b1c92

## State Impact

- target: wild-horizon-5461 — Corrects the forty-pair truncation recorded in happy-dawn-1960: f2bf2c83 reports every failing pair with its names, distance and volume, pinned by two sixty-failure fixtures and documented in CLI.md and ADR-346. Full CLI suite on that commit: 636 passed, 1 skipped in 515.14s, exit 0. Engine suite and packaged gate not rerun for this CLI-only correction; no F9 claim.
