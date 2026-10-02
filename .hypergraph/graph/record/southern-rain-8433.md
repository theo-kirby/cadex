---
node_id: da1725f5-28c0-5cc9-8a1e-273b7889bbde
slug: southern-rain-8433
title: 'ot11 R1: r21b published (row 33), valid, 2 of 10; a warm start resets exploration and lost r19''s gait'
created_at: '2026-10-01T16:15:10+00:00'
parents:
- forest-rose-3078
summary: ''
---
## What

Published walk session 7's second round, `r21b-r19-continue`, on `ot11-quad-1`: run row 28, evaluation row 33. **Valid, 2 of 10 (1103 and 1108 pass every predicate).** Receipt `docs/probes/ot11/retained/p7-quad-1-r21b-evaluation.json` (no machine paths); both ledgers regenerated with the runner scripts (`ot11-runs.json`: 28 runs, 26 attempts, 46,370.91 s, `r22-gentle-contact25` in progress; `ot11-evaluations.json`: 33 evaluations, 12 judge scores); seed-1101 filmstrip (173 KB) and detail (232 KB) committed; `REPORT.md` updated in every section (run table, totals, warm-start list, evaluation row and reading, revision row, failure item, remaining defects) and `cli/tests/test_ot11_report.py` counts moved with it.

## Why

The critic's accepted-message named this unit: when r21b's evaluation lands, publish it the way r20 was published. It had landed (the agent's own evaluate call, ledger `evaluated`, 2 passed) and session 7 had moved on to r22, so the GPU was not idle and no second job was started. It serves **R1** (every earlier run and evaluation published) and **C1** (the report lists every run, evaluation and revision).

On the critic's other demands, what I did instead and why:
- **Reconcile due**: not done. This dispatch is a work iteration, and its instructions forbid the reconcile skill, `hypergraph update` and state writes without exception. The tail is now two records (forest-rose-3078 and this one) plus the plan impacts on young-crane-9546, late-valley-7350 and strong-birch-7412; the next reconcile pass should fold them.
- **"Banned bet, choose a different criterion"**: the plan's short bet (young-crane-9546: rollout-pose clearance, section plane) is not about any ot11 criterion, and I did not work it. Against the charter, one line each:
  - P1, P2, P3, P4: evidence recorded (contract frozen, negatives measured, `cadex evaluate`, `assembly.goal`, loop with ≥3 measured rounds on reach and walk). Owner ticks remain.
  - R2: confirmation `r2-confirm-1` passes 10 of 10 and the judge's bar. Owner tick remains.
  - R3: confirmation `r3-confirm-1` passes 10 of 10 and the judge's bar. Owner tick remains.
  - **R1: the only unmet criterion.** Not blocked; it is hard. 21 walk attempts, best 9 of 10 (r19).
  - C1: waits on R1 or the 72-hour ceiling (run started 2026-09-30 07:04Z, ceiling 2026-10-03 07:04Z).
  So "a different criterion" has no open target that is not R1. The frontier "not moving" is R1 not moving; this unit moves R1 by a diagnosis, below.
- **Bet (for the next model to adopt; the planner is off and I may not edit the plan)**: *R1 — warm starts must continue a policy, not restart its exploration.* See Result.

## Method

- Checked validity the way r20 was: `contact_offsets` empty; model `6cecfa2d…` (r17–r20 lineage, ADR-469 spring); task `db670704…` equals the trained task and r19's; spec block in script_history 0105 byte-identical to 0101's (r20's evaluated block) and to the frozen `walk-spec-block.txt` except HIP_MM/WEIGHT_N, which equal the rig (96.7006 mm, 5.05069617762 N).
- Built the receipt's `evaluation` section with a throwaway builder that first reproduced r20's published section exactly from r20's `evaluation.json` (only `trained_model_sha256` comes from the registration), then ran it on r21b.
- Regenerated ledgers: `eval_ledger.py --judges docs/probes/ot11/retained` over w2-negative, robin-negative, robin-1, heron-1, quad-1; `run_ledger.py` over robin-1, heron-1, quad-1. Diffs were appends only.
- Read both train logs and `training/cadex_train.py --init-from`: only the actor is loaded; `log_std` comes from `--initial-std` (default 0.30) and the critic starts fresh.
- Tests: `cli/tests/test_ot11_report.py` 13 passed; full `cli/tests` CPU-only (`CUDA_VISIBLE_DEVICES=`): 1273 passed, 1 skipped.

## Result

- **r21b: 2 of 10, valid.** W7 slip fails 8 (0.135–0.192 against 0.15; rear-left the worst foot on nine seeds, front-right on 1108). W9: 1109 passes (1.400, from r19's 1.571), 1101 fails (1.600). W5-share fails 1101 and 1110 (0.695, 0.696), W8-low fails 1109 (0.395). No seed tips; tilt 23.6–27.2° (r19: 7.9–22.9°). Training 750 iterations, 2,068.98 s GPU, final 3.65/step (best 3.90 at 694).
- **Diagnosis, measured**: r21b trained r19's *identical* task warm from r19 and lost r19's gait the same way r20 did. Both open at ~+2 then ~−2 per step (r20 +1.97, −2.03; r21b +2.19, −1.64) against r19's final 4.47, because `--init-from` loads only the actor, resetting action noise to 0.30 (r19 ended at 0.177) and the critic to fresh. So r20's slip regression was the warm start, not `contact_w` 3.5. The agent reached the same conclusion itself and registered `r22-gentle-contact25` (`initial_std` 0.12, `learning_rate` 5e-5, `contact_w` 2.5), which is training now under session 7's driver.
- **Handoff — what was tried**: 21 walk attempts over 7 sessions; reward revisions moved slip, W9 and W10 in turn; r19 reached 9 of 10 (only 1109 W9 1.571). Two warm-start continuations from r19 both regressed to slip failures.
- **Handoff — what to try next, in order**: (1) when r22's evaluation lands, publish it the same way (receipt, ledgers, spec-block check, CPU `cli/tests`); if 10 of 10, pre-register the confirmation evaluation and the judge's bar before anything else. (2) If r22 still loses r19's gait in its first iterations, the next product unit is **a trainer fix, not a reward change**: `--init-from` should carry the source policy's `log_std` (the `.cxpolicy` already stores it, `training/cadex_train.py` ~2391) unless `--initial-std` is given, with a regression test that fails today, tested under pixi and the training venv. That is pipeline work the actor may do; it never touches the agent's reward or spec. (3) Session 8 must be pre-registered and committed before launch.
- Concern: the reconcile is overdue (see Why). No new dependency. No GPU job started by the actor.

Dispatch closed: 1 unit — published r21b (row 33, valid, 2 of 10) and measured that a warm start resets exploration and loses r19's gait

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 0d4ae72fc2f2046ba8f45737bb3448582279bdb2

## State Impact

- target: smooth-fountain-9832 — r21b-r19-continue (run row 28, evaluation row 33) published: valid, 2 of 10 (1103, 1108); r19's identical task warm from r19 fails slip on 8 (W7 0.135-0.192), so r20's regression was the warm start (--init-from loads only the actor; action noise reset to 0.30 vs r19's 0.177, fresh critic), not contact_w; r22 (initial_std 0.12, lr 5e-5) is training; commit 0d4ae72f
- target: golden-bay-4173 — REPORT.md carries run row 28 (28 runs, 26 attempts, 46,370.91 s GPU) and evaluation row 33 (33 evaluations), revision row and failure item for r21b; cli/tests CPU 1273 passed, 1 skipped
