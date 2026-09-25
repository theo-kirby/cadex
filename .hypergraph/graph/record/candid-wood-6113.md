---
node_id: cd400843-b768-5152-a5ee-07ecafc206ca
slug: candid-wood-6113
title: 'ot9 rung 4: fresh-process reopen of r3-ppo-1 and frozen ten-seed evaluation, 10/10 pass'
created_at: '2026-09-22T19:33:20+00:00'
parents:
- hidden-wing-6674
summary: ''
---
## What

Short-ladder rung 4 of ot9, plus the missing half of B2.
- **Fresh-process reopen:** a new `./cadex export` process rebuilt the accepted policy revision of `ot9-robin`, and I recorded its identity against the r3 installation receipt.
- **Frozen evaluation:** I ran the ten-seed evaluation from `docs/probes/ot9/README.md` on policy `r3-ppo-1` (`ef71f370`) and read every seed with `runner/balance_eval.py` against the MJCF and task pins.
- **Where it is:** compact receipt `docs/probes/ot9/retained/r4-robin-eval-1.json`, a regression in `cli/tests/test_ot9_balance_eval.py` and a README section. Commit `e5e181c9`.
- No product turn, and no design, task, reward or tooling change.

## Why

The critic named this unit: close B2 with a fresh-process reopen showing the same policy and model digests, then run the frozen ten-seed evaluation (8 s, 50 Hz, 30°, `fallen`), publish every seed and cover it with a regression. Done as asked, with no deviation. The target is the ot9 charter root `open-cabin-5892`, through B2 (`tidy-arbor-3203`) and B3 (`early-rain-5934`).

## Method

- **Reopen:**
  - Ran `./cadex export --project $PROJECTS/ot9-robin --out $PROJECTS/ot9-robin/reopen/r4-fresh --json` in a new process: exit 0, 199.5 s, project commit `79b226b`.
  - Compared its revision and digest with `installation.policy_on` in the r3 receipt.
  - Hashed its policy receipt, MJCF, task, stored `.cxpolicy` and rollout trace.
- **Evaluation:**
  - For S in 0–9, in order: `./cadex params --project $PROJECTS/ot9-robin --set rollout_seed=$S --out $PROJECTS/ot9-robin/eval/r3-ppo-1/seed-$S --json`. Every seed exited 0 in 200–201 s; project commits run `0b00a40`…`997ac9e`.
  - Read all ten with `balance_eval.py --expect-mjcf 933b1ac6… --expect-task 1f8c1040…`. The full report is project-local at `eval/r3-ppo-1/balance-eval.json`, project commit `152410c`.
  - Added chassis xy drift per seed from each trace as a diagnostic only.
- **Regression:** the new test `test_the_first_ten_seed_evaluation_is_every_seed_on_one_reopened_policy` checks:
  - the reopen equals the installed revision `df58d4ff` and digest `6ff77527`;
  - policy, MJCF and task equal the r3 policy and the contract pins, and the witness error is under tolerance;
  - the reopen trace equals r3's seed-0 trace;
  - the seeds are exactly the contract's 0–9;
  - each row's pass is recomputed from the bar (steps, 401 frames, 8.0 s, truncation, no `fallen`, tilt ≤ 30°);
  - there are ten distinct traces;
  - `candidate_verdict` is recomputed from the rows, not copied.
- **Tests:** `pixi run python -m pytest cli/tests` gave 931 passed and 1 skipped. The engine suite was not run because nothing under `src/` changed.

## Result

**B2's identity check holds in a fresh process.**
- The reopen rebuilt accepted revision `df58d4ff825e3c02…` to digest `6ff77527a39e22f4…`, equal to the installation.
- The policy receipt (sha `8df0c267`, byte-identical to r3's) names:
  - policy `ef71f370a2f18966…`, equal to the stored `assets/r3-ppo-1.cxpolicy`;
  - model `933b1ac6…` and task `1f8c1040…`, equal to the pins and to the exported files;
  - witness error 6.93e-8 against a 1e-4 tolerance, over 32 samples;
  - training seed 1001 and 300 iterations.
- Its rollout trace is byte-identical (`6db76948`) to the installing chain's seed-0 trace, so the rebuild is deterministic across processes.

**B3's first candidate evaluation is completed, and the candidate verdict is `pass`: 10/10 seeds.**

| seed | duration | termination | peak tilt | min height | reward | drift |
|---|---|---|---|---|---|---|
| 0 | 8.0 s | truncated | 5.352° @0.06 s | 105.37 mm | 393.47 | 838 mm |
| 1 | 8.0 s | truncated | 3.975° @0.06 s | 105.13 mm | 393.25 | 847 mm |
| 2 | 8.0 s | truncated | 4.850° @0.08 s | 105.82 mm | 393.68 | 829 mm |
| 3 | 8.0 s | truncated | 3.793° @0.06 s | 105.54 mm | 393.31 | 848 mm |
| 4 | 8.0 s | truncated | 3.048° @0.06 s | 105.55 mm | 393.46 | 843 mm |
| 5 | 8.0 s | truncated | 5.130° @0.06 s | 105.05 mm | 393.41 | 841 mm |
| 6 | 8.0 s | truncated | 4.877° @0.06 s | 105.34 mm | 393.63 | 834 mm |
| 7 | 8.0 s | truncated | 3.173° @0.06 s | 105.36 mm | 393.33 | 845 mm |
| 8 | 8.0 s | truncated | 3.063° @0.06 s | 105.71 mm | 393.62 | 839 mm |
| 9 | 8.0 s | truncated | 2.783° @0.06 s | 105.83 mm | 393.33 | 848 mm |

- Every seed ran 400 steps at 50 Hz with 401 solver frames.
- Every seed ran on policy `ef71f370`, MJCF `933b1ac6` and task `1f8c1040`.
- `fallen` fired on no seed; none is void and none failed.

Concerns and assumptions for the next iteration:
1. **Drift.** The policy drives about 0.84 m in nearly the same direction on every seed (ending near (−365, 758) mm). This is systematic and not a balance failure. The bar does not measure position, and I did not judge it. It belongs in the B5 report as a remaining defect or behaviour. Shove recovery and position-holding are long-rung items and do not substitute for B3.
2. **Per-seed accepted revisions.** `rollout_seed` is a script literal, so the project's accepted revision now sits at seed 9 (`ae889a9b…`, commit `997ac9e`). Policy, model and task are unchanged. Anything that pins "the accepted revision" should note this.
3. **Iteration 6 residue.** The interrupted iteration 6 left four unaccepted attempts under `script_artifacts/df58d4ff…/`, an uncommitted `latest_candidate` change in `script.json`, and an empty `eval/r3-ppo-1/` directory before this run. It produced no evidence, and I classified it as interrupted in the receipt.
4. **What remains.** B4 (fit, swept fit and inventory on the final design, compared with the baseline) and B5 (both suites, the fresh reopen at the final revision, `REPORT.md`) are still open. No design change was made, so B4's comparison is against an unchanged design.
5. The unreconciled tail is 1 record.

No new dependency. No policy binary or trace is committed; the repo holds only digests and project-relative paths.

Dispatch closed: 1 unit — fresh-process reopen of ot9-robin reproduced r3-ppo-1's accepted identity (df58d4ff/6ff77527, policy ef71f370, model 933b1ac6, task 1f8c1040, byte-identical trace), and the frozen ten-seed evaluation passes 10/10 (8.0 s each, no fallen, peak tilt ≤5.35°, min height ≥105.05 mm), receipt r4-robin-eval-1.json with a regression.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot9
- commit: e5e181c9b8a1225d303a4503007c1c833cc3fca4

## State Impact

- target: tidy-arbor-3203 — fresh-process reopen (cadex export, new process) rebuilt accepted df58d4ff to digest 6ff77527 with policy ef71f370, model 933b1ac6, task 1f8c1040, witness 6.9e-8; trace byte-identical to the installing chain's seed-0 trace; B2's identity check is met (commit e5e181c9, docs/probes/ot9/retained/r4-robin-eval-1.json)
- target: early-rain-5934 — frozen ten-seed evaluation of r3-ppo-1 completed on pinned artifacts: verdict pass, 10/10 seeds ran 400 steps / 8.0 s by truncation, no fallen, peak tilt 2.78-5.35 deg (reset transient), min chassis height >= 105.05 mm; systematic ~0.84 m drift reported, not judged (commit e5e181c9)
