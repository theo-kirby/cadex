---
node_id: 9f7f4722-d260-5c93-99a1-79166bf41162
slug: wild-fountain-1112
title: 'ot11 R1: walk session 8''s r23 (agent-stopped, no policy) published as run row 30; r24 (value_weight 0.05) live, W10 model clean'
created_at: '2026-10-01T17:31:57+00:00'
parents:
- brave-spark-6208
summary: ''
---
## What
I published walk session 8's first run, `r23-r19-clip05`, and checked on its second, `r24-r19-vw005`, which is still training.
- `retained/ot11-runs.json` was regenerated with `run_ledger.py` over ot11-robin-1, ot11-heron-1 and ot11-quad-1. It now has 30 runs and 28 attempts, 48,359.28 s supervised, and `in_progress: [r24-r19-vw005]`. The only change is the new row plus `in_progress`.
- `REPORT.md` changes:
  - run table row 30 (`stopped`, 87 iterations, 261.25 s, no trainer time);
  - totals: walk 24 / 43,011.30 s, all 30 / 48,359.28 s;
  - the warm-start list, and the in-progress sentence;
  - a new *Every failure* item, "One run was stopped by the agent and saved no policy";
  - session 8's line in *Remaining defects*.
- `cli/tests/test_ot11_report.py` counts are 30 runs and 28 attempts. A new pin checks that exactly one run is `stopped`, that it is r23 with no policy, and that the failure section says so.

## Why
The critic named R1 (`smooth-fountain-9832`): publish session 8's runs as they end, check the W10 rule, and if the session is still running, heartbeat it.
- r23 ended (stopped by the agent through `train_stop`). r24 had not ended, so there is no evaluation to publish yet, and row 35 is still owed.
- Before the unit, the critic asked for a backfilled record for ADR-472. I minted it as `brave-spark-6208`, impact on C1 (`golden-bay-4173`).
- **Deviation:** the critic also asked me to fold the two unreconciled records. This dispatch forbids reconcile in a work iteration, so I did not fold. The tail is now 3 unreconciled records (frosty-crow-0794, brave-spark-6208 and this one), which meets the three-record trigger for the next reconcile pass.

## Method
- Read `loop-ledger.jsonl` and each run's `registration.json` and `training-status.json` in `ot11-quad-1`.
  - r23: warm from r19, clip 0.05, seed 231, budget 3,500 s, stopped at iteration 87 after 261.25 s, `policy_sha256` null.
  - r24: warm from r19, `value_weight` 0.05, seed 241, budget 3,500 s, checkpoints every 25, started 17:20:49Z.
- W10 rule: `grep` on r24's `train/model-model.xml` finds no `margin=` or `gap=` attribute. Its sha256 begins `6cecfa2d`, identical to r19's model and the pre-registration's.
- Heartbeat at 17:31Z: rounds.py (pid 3721392) and the trainer (pid 3740154) are alive. r24's reward per step at iterations 0/20/56/95/119 was +3.67/+3.04/+3.33/+3.60/+3.80, with total loss about +67 to +77, against r23's +596 to +652 and its fall to +0.72 by iteration 74. That is a training-curve reading only, not an evaluation.
- `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests/test_ot11_report.py cli/tests/test_ot11_conformance.py cli/tests/test_ot11_rounds.py -q` gave 39 passed. The receipt has no `/home/` path.

## Result
- Session 8 is live and supervised under setsid, and the GPU belongs to it. r24 should end at its 3,500 s budget by about 18:19Z, or earlier on the agent's stop. Its curve has so far held near r19's level rather than falling as r20–r23 did. That is not evidence for R1 until it is evaluated.
- No code under src, cli/cadex_cli or training changed, so the full suites were not re-run.
- **Handoff.** What I tried: publishing each session-8 run as it ends, plus a heartbeat. What to do next:
  1. When r24 ends and is evaluated (loop-ledger `evaluated`), publish it as evaluation row 35, the way r22 was published:
     - rebuild both ledgers (`run_ledger.py`, `eval_ledger.py`);
     - check that its `contract_deviations` is empty;
     - check its contact offsets and margin/gap;
     - add a filmstrip of 300 KB or less;
     - add the revision row (r23 has none because it has no evaluation) and update the test counts.
  2. If r24 passes 10 of 10, pre-register and commit the R1 confirmation with the judge bar before running it.
  3. A reconcile pass is due: 3 unreconciled records.
- No new dependency.

Dispatch closed: 1 unit — session 8's r23 (stopped by the agent, no policy) published as run row 30; r24 heartbeat, W10 model check clean, row 35 owed when it is evaluated

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 44fde231da2a6f85a36b8a7e5844a73fe1e875d2

## State Impact

- target: smooth-fountain-9832 — walk session 8 run 1 r23-r19-clip05 (warm from r19, clip 0.05) stopped by the agent at iteration 87 (261.25 s) as reward/step fell 4.40 -> 0.72, no policy, no evaluation; published as run row 30 (30 runs, 28 attempts, 48,359.28 s). Run 2 r24-r19-vw005 (value_weight 0.05) in progress on model 6cecfa2d with no margin or gap; evaluation row 35 owed
