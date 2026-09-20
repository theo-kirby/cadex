---
node_id: 1cdc299f-4402-5713-9f6a-c453f9c36346
slug: clear-clock-9191
title: Recover ot7 deadline crash with verified relative budget (ADR-385)
created_at: '2026-09-19T17:29:26+00:00'
parents:
- steady-sail-9171
summary: ''
---
## What

Replaced ot7's timezone-bearing absolute deadline with a fresh relative
48-hour budget, at the owner's explicit authorization (ADR-385). Kept Opus
for every role and preserved the experiment outcomes and remaining slots.

## Why

The September 17 Opus restart completed reconciliation at iteration 151,
then crashed in BudgetClock.should_stop comparing offset-naive and
 offset-aware datetimes. The operator's absolute deadline triggered the
incompatibility. The process never dispatched Robin's Opus continuation.
The notifier stayed alive and reported the dead process, then periodic
reports. The owner approved correcting the deadline and restarting.

## Method

Read the loop status, logs, tmux traceback, watcher pane and project receipts.
Set stop.until to null and retained stop.after at 48h. Tested the installed
runner's Config and BudgetClock directly using a controlled clock: startup
and one second before expiry return no stop, exactly 48h returns the wall
clock stop. Asserted every role still selects claude-opus-5. The live
experiment window probe succeeded: allowed, room true, five-hour 1%, weekly
1%, exit 0. No frozen prompt was dispatched by this check.

## Result

The configured budget path no longer reaches the failing datetime comparison.
This is an operator configuration repair, not a patch to the external runner.
Robin remains at one completed Fable create turn with three continuations
unspent; Plover remains unattempted. The next substantive unit is Robin
continue-1 with an explicit Opus override. No product code changed and the
previous 832-pass CLI suite remains the baseline. Launch and notifier
liveness must be checked after the restart; this record does not assert
that the process is already running.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: e47a28998c541979b46322e2428b0bc34e019773

## State Impact

- target: mild-ledge-7157 — Opus restart crashed after iteration 151 reconciliation due to naive/aware deadline comparison; owner authorizes fresh 48h relative budget with until null; next design work remains Robin continue-1 and Plover
