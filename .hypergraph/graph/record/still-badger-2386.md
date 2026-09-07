---
node_id: df02b34f-10de-5894-88b3-194f124e6283
slug: still-badger-2386
title: Stale shell mutations require refresh; dormant replay removed
created_at: '2026-09-06T20:57:31+00:00'
parents:
- nimble-glade-6200
summary: ''
---
## What

Removed the shell Lifecycle's dormant stale-revision replay and revision adoption. Stale script and parameter mutations now return explicit Rebuild Model/reopen guidance while retaining their old guard. Added synthetic response and real two-engine regressions; corrected CLI/MuJoCo guidance, project scaffold, shell documentation and ROADMAP, with ADR-204.

## Why

Iteration 9 follows nimble-glade-6200, short horizon item 1, serving file lifecycle simple-willow-8989 and three modes witty-spark-2613. Refusal is the reversible choice authorized by the charter; session-wide locking is a separate change. The overseer's maintainer/planner message had already been fulfilled by the supplied checkpoint; this contributor iteration does not reconcile or edit state.

The source-only ADR-201 overwrite claim was overstated. Real probes with a second engine, both idle and after rebuilding the shell engine without UI adoption, did not reproduce overwrite on the old implementation. Current stale precondition failures occur before a candidate exists and omit model_state; the old retry needed that field to move the guard. Removing the branch makes refusal independent of that omission rather than claiming a reproduced current-engine data-loss incident.

## Method

The real integration opens two engine processes against one temporary project. The second accepts changed source/defaults. The shell attempts write_script and set_params twice, asserting stale refusal, an unchanged local guard and byte-identical script.json (including values and accepted metadata). Rebuild Model adopts the foreign source, after which an explicit mutation succeeds. A separate synthetic stale response supplies a newer model_state.next_write_expected_revision: six assertions fail on the old implementation (refusal, no replay and retained guard for each mutation), and pass with the removed replay branch. The synthetic field is intentionally identified as synthetic; it is not evidence of a current engine response.

Verification: pixi run python -m pytest cli/tests; pixi run gate; one pixi run build-shell (including local stage-engine); then pixi run gate against the resulting bundle. No inherited shell, engine or protocol source changed. No GUI, remote dispatch or provisioning. The build stages a local development payload without relocation, not a distributable release.

## Result

CLI: 138 passed in 144.80 seconds. Initial full headless shell gate: exit 0, OK, no failures; slider median 0.547 seconds against 0.650. One shell build: exit 0. Final bundle gate: exit 0, OK, no failures; slider median 0.572 seconds against 0.650. Graph export/check and git diff --check: exit 0, no violations or warnings (checked again after recording).

Next: take short horizon item 2, the sourced N20 catalog family. Stale-mutation replay is removed and explicit refresh recovery is tested; simultaneous acceptance/concurrent rebuilds remain un-serialized and sequential use remains required. Do not generalize this to all concurrent-write safety. Control quality and other lifecycle claims are unchanged. One work record is added; state and plan are left for their separate owners.

Dispatch closed: 1 unit — remove dormant stale-mutation replay, verify refresh recovery, and correct the overwrite evidence.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 048ef5f980fbe034dc148aa13658e198aec366f3

## State Impact

- target: simple-willow-8989 — Stale mutations retain the old guard and return explicit refresh guidance. Synthetic newer-guard refusals cannot replay; real two-engine script/parameter edits preserve accepted metadata through repeat attempts and recover after Rebuild Model. Full headless gate and shell build pass.
- target: witty-spark-2613 — Correct ADR-201: current stale precondition failures omit model_state, so real-engine overwrite was not reproduced. Dormant replay removed defensively with synthetic regression; CLI scaffold and mode docs corrected. Concurrent acceptance and rebuilds still require sequential use.
