---
node_id: c871cc89-f987-5d88-8c40-b22248a54f45
slug: forest-rose-3078
title: 'ot11 P4: rounds.py does not count refused starts (attempt: false) as session runs'
created_at: '2026-10-01T15:52:53+00:00'
parents:
- deep-moss-5363
summary: ''
---
## What
`docs/probes/ot11/runner/rounds.py` no longer counts a refused start as one of a session's runs. A refused start is a `train_ended` row whose run status is `failed` with no iteration run, which `run_ledger.py` marks `attempt: false`. `standing()` now reads `runs/<run>/training-status.json` for such rows, reports them as `refused_this_session`, and leaves them out of `settled_this_session`. If the status can't be read, the run still counts. The registration's `stop_rule` text says so. Commit `f7d131d4`. REPORT.md has a bullet on the session 7 effect.

## Why
Target: R1 (`smooth-fountain-9832`), and P4's driver. The critic asked for this fix before any session 8, with a test that fails on the current code. The critic also named publishing r21b as the next unit. That run was still training when this iteration started (it finished 750 of 750 iterations at about 11:46 EDT), and the product agent's session 7 turn still has to evaluate it. So I took the other critic-named fix, which could be finished now, rather than wait on a live session. Deviation: r21b is not published this iteration. The banned bet is young-crane-9546 (stale clearance-over-poses). I did not touch it.

## Method
- Added `refused(project, row)` using the same rule as `run_ledger.py:67`.
- New test `test_a_refused_start_does_not_use_up_a_round`: a refused start is not counted, a failure after 40 iterations is counted, and a missing status is not forgiven. Updated the expected dict in the existing standing test.
- With rounds.py stashed (old code), the new test fails. With the fix, all 11 pass.
- Read the real `ot11-quad-1` ledger with session 7's registration (`runs_ended_before` 19, `max_runs` 3). The new code gives `settled_this_session` 1 and `refused_this_session` 1. The old code gave 2.
- `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`: 1273 passed, 1 skipped (18m47s).

## Result
For any session after 7, a refused start no longer uses up a run. Session 7's running driver keeps the code it launched with, so it still stops after r21b is evaluated, with two runs trained, as pre-registered. REPORT.md says this.

Handoff (the critic asked for one; a different model takes the next turn). What has been tried on R1: 21 walk runs over 7 sessions on ot11-quad-1. r19 passed 9 of 10 seeds, failing W9 on seed 1109 (1.571 vs 1.5). r20 (contact_w 3.5) got 0 of 10. r21b continues r19's task unchanged and has finished training; its evaluation is pending in the session 7 turn.
Next:
1. When session 7's evaluation of r21b lands, publish it the way r20 was published: hashes, spec-block token check, no contact offsets, run and evaluation ledgers, cli/tests on CPU.
2. If r21b reaches 10 of 10, pre-register the confirmation evaluation and the judge's bar before anything else.
3. Otherwise pre-register session 8 with the fixed driver and commit it before launch.

If R1 stays stuck, R3 (balance) and R2 (reach) are the other open behaviour criteria. Check the README and REPORT for where they stand before switching. The GPU stays busy only while a walk job runs.

The critic noted 6 pending plan impacts (young-crane-9546, late-valley-7350, strong-birch-7412) that the planner, which is off, will never fold. The next reconcile should fold them or record why not. Work iterations cannot reconcile.

Dispatch closed: 1 unit — rounds.py stops counting refused starts as session runs, with a regression test that fails on the old code; r21b is not yet published

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: f7d131d4b1e9deb7e24c278659817985795414c2

## State Impact

- target: smooth-fountain-9832 — the walk driver rounds.py no longer counts a refused start (failed with 0 iterations) as a session run (f7d131d4, regression-tested); session 7 keeps its launch code; r21b trained 750/750 and awaits evaluation and publication
