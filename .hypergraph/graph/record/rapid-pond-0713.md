---
node_id: af2288c9-fdb4-5274-9c03-8baacb702a0a
slug: rapid-pond-0713
title: 'ot11 R1: r24-r19-vw005 published (run row 31, evaluation row 35): valid, 10 of 10 on the frozen walk spec; confirmation owed'
created_at: '2026-10-01T18:45:57+00:00'
parents:
- wild-fountain-1112
summary: ''
---
## What
I published walk session 8's second and last run, `r24-r19-vw005`, as run row 31 and evaluation row 35 (commit `6a842d43`). **It passes the frozen walk spec on all 10 seeds.** It is the first walk evaluation to do so. It is the agent's own evaluation and not a pre-registered confirmation, so R1 stays open.
- Ledgers regenerated: 31 runs, 29 attempts, 51,860.52 s, and no run in progress; 35 evaluations, 31 conforming, 12 judge scores.
- `retained/p8-quad-1-r24-evaluation.json` is the receipt, built like r22's: registration, how the run ended, the evaluated checkpoint and who chose it, the spec-block check, per-seed episodes, metric and reward-term min/max, and a diagnosis.
- Filmstrip, seed 1101: overview 174 KB and detail 221 KB, on the dark floor.
- `REPORT.md` changes:
  - run row 31 and the totals (walk 25 runs / 46,512.54 s);
  - the warm-start list, and the in-progress sentence;
  - evaluation row 35 and its row note;
  - revision row `r24-r19-vw005`;
  - *Every failure*: "Thirty of 35", "Eight runs ended at their wall-clock budget";
  - *Remaining defects*: R1 now waits on a confirmation, not on a passing round.
- Test pins in `cli/tests/test_ot11_report.py` and `test_ot11_conformance.py` moved to the new counts. Pass list: [5, 6, 11, 12, 35].

## Why
This is the critic's named unit, on R1 (`smooth-fountain-9832`): "when r24-r19-vw005 ends, publish it the way r23 was published ... evaluation row 35, both ledgers, the filmstrip, REPORT rows and CPU-only cli/tests. If it passes 10 of 10, pre-register and commit the confirmation and the judge's bar before running it."

The same message also said "the current bet is now banned" and asked for a bet on a different criterion. I read "the current bet" as the plan's short rank-1 clearance-sweep bet, which serves no ot11 criterion. I did not work it. R1 is the criterion I chose, and this unit moved it more than any in 54 iterations: from 9 of 10 at best to 10 of 10 on a valid evaluation.

**Deviation:** I did not pre-register the confirmation in this iteration. Publication was the one unit. The confirmation needs its own reviewed registration, and the critic required it to be committed before it runs. It is the next unit.

## Method
1. Waited, inside this iteration, for r24 to end. It hit its 3,500 s budget at iteration 924 with no final policy (`training-status.json`, exit −15, 3,501.24 s).
2. The agent installed the iteration-900 checkpoint (`walk_task.000900.cxpolicy`, sha 5aaf21e7) as `walk_r24.cxpolicy` in script revision 0112 (7df101b0) and evaluated it once. `loop-ledger.jsonl` has one `evaluated` entry for r24: pass, 10 of 10. Then the agent ended session 8. `turn.json`: exit 0, 4,269.6 s; `standing_after.passed: true`, so the rounds driver's stop rule fired. Its closing message says it took the last checkpoint "not by any evaluation-seed result".
3. Validity checks:
   - `grep -cE 'margin=|gap='` on r24's `train/model-model.xml` gives 0, and `contact_offsets` is `[]`.
   - The evaluation's model sha 6cecfa2d equals the registration's. Its task sha db670704 equals the trained task, which is r19's.
   - The script's spec block, compared line by line with `retained/walk-spec-block.txt` (frozen 487416af), differs only in `HIP_MM` (96.7006) and `WEIGHT_N` (5.05069617762). Both equal the rig the report states. The block is byte-identical to script_history 0098 (r19) and 0108 (r22).
   - 0111 → 0112 differs only on the policy line.
   - `eval_ledger.py` gives `contract_deviations: []`.
4. Ran `run_ledger.py` (robin-1, heron-1, quad-1) and `eval_ledger.py` (w2-negative, robin-negative, robin-1, heron-1, quad-1) in the projects' established order, then built the receipt with a one-off script. It has no `/home/` path.
5. `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests -q`: **1288 passed, 1 skipped** (1,101 s). The three ot11 files alone: 39 passed. No engine, cli/cadex_cli or training code changed, so `test-engine` was not re-run.

## Result
- **Row 35 is a valid 10 of 10 on the frozen walk spec.** W9 is 1.0–1.3; seed 1109 was 1.571 under r19. Also:
  - W7 slip 0.081–0.111;
  - W3 0.955–1.008;
  - clearance 0.275–0.297 hip heights;
  - duty 0.437–0.608;
  - W10 lowest foot −0.019 to −0.012 hip heights, on a model with no margin or gap;
  - 8–13 steps per foot;
  - all ten seeds run to the horizon.
- The thinnest margin is W2 tilt, 24.2° at most against 30°.
- **What changed.** After iteration 1, training never fell below +2.96 per step. r20–r23 fell to about +0.3 to +1.3, and the total loss sat at about +66 to +97 against r23's +596 to +652. That fits the untrained-critic diagnosis, but no ablation separates it from the seed.
- **Project state:** `ot11-quad-1` declares `walk_r24.cxpolicy` at revision 7df101b0. Session 8 has ended, and the GPU is free.
- The unreconciled tail is 1 record (this one).
- **Handoff.** Tried: publishing each session-8 run as it ended. Next unit, R1's confirmation, before any run:
  1. Write `retained/p4-quad-1-r1-confirm-registration.json` in the shape of `r3-confirm-1-registration.json` and `r2-confirm-1`:
     - the revision 7df101b0;
     - policy 5aaf21e7, model 6cecfa2d, task db670704 and spec block 487416af with this rule;
     - the frozen seeds;
     - the judge's bar from `contract.json` and README, and the judge seeds;
     - the void rules (no margin or gap; W10 frozen).
  2. Commit it. Only then run `cadex evaluate` once, with key `r1-confirm-1`, and `runner/judge.py` on the declared seeds.
  3. Also required: R1 says the policy is "installed, verified and reopened through the supported path". Verify and reopen `ot11-quad-1` through `cadex` as part of that registration.
  4. Never re-run the confirmation to fish for a pass.
- No new dependency.

Dispatch closed: 1 unit — r24-r19-vw005 published as run row 31 / evaluation row 35: valid, 10 of 10 on the frozen walk spec (the agent's own evaluation, not R1's confirmation); full cli/tests 1288 passed CPU-only

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 6a842d43eb714e9de0e253f029905155a51b7cd9

## State Impact

- target: smooth-fountain-9832 — walk session 8 ended: r24-r19-vw005 (warm from r19, value_weight 0.05, budget-stopped at it 924) iteration-900 checkpoint, the agent's own evaluation row 35, passes the frozen walk spec 10 of 10 (W9 1.0-1.3, slip 0.081-0.111, tilt <=24.2 deg), valid (no margin/gap, model 6cecfa2d, task db670704, spec block per rule, no contract deviations); ot11-quad-1 declares walk_r24 at 7df101b0. Not R1 yet: no pre-registered confirmation or judge score; that is the next unit
- target: golden-bay-4173 — ledgers 31 runs / 29 attempts / 51,860.52 s and 35 evaluations (31 conforming); REPORT rows and pins updated; full cli/tests 1288 passed 1 skipped CPU-only at 6a842d43
