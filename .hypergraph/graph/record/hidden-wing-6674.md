---
node_id: 6d76e75e-02f3-5aaf-a08b-c8abdd42c0db
slug: hidden-wing-6674
title: 'ot9 rung 3: first PPO run r3-ppo-1, policy installed, seed-0 rollout read'
created_at: '2026-09-22T18:37:39+00:00'
parents:
- windy-tide-4050
summary: ''
---
## What

Short-ladder rung 3 of ot9: the first bounded offboard PPO run on `ot9-robin`. I installed its policy through the supported script path and read one rollout. Settings, step budget, stop rule and run accounting went into `docs/probes/ot9/retained/r3-robin-train-1.json` and were committed as `41d97bb9` **before** the trainer started. Results are in commit `34f310b5`, in the same receipt. No product turn and no design, task or reward change.

## Why

The critic named this unit: rung 3, with the training seed, settings, step budget, stop rule and void/interrupted accounting recorded before the run starts. Then install the `.cxpolicy` through the supported CLI path, run one rollout, and check the first real trace's frame count against the reader before reporting any seed. Done as asked. One choice to state: the policy installed is the **final** iterate (`ef71f370`), not the trainer's best-reward checkpoint (`dc4d392e`, iteration 255). The plan said "the resulting .cxpolicy", and reward is not a selection criterion under this contract.

## Method

- **Plan (committed first):** `./cadex train --project $PROJECTS/ot9-robin --out runs/r3-ppo-1 --put --name r3-ppo-1.cxpolicy --iterations 300 --envs 1024 --seed 1001 --label r3-ppo-1 --timeout 2400`.
  - Every other setting is the trainer's default: unroll 20, epochs 4, hidden [64,64], lr 3e-4, discount 0.97, entropy 1e-3, initial std 0.3, no action filter, no slew limit, no warm start.
  - Budget: 6,144,000 control steps.
  - Stop rule: 300 iterations or 2400 s. No early stop on reward, no restart inside the unit.
  - Seed 1001 is deliberately outside 0–9.
  - The trainer venv's jax backend was checked as `gpu` beforehand.
- **Install:**
  1. `cadex script` (read).
  2. `cadex_cli.walk.declare_policy` rewrote only the two literals, to `weights="r3-ppo-1.cxpolicy"` and `sha256="ef71f370…"`; a diff confirmed only those two lines changed.
  3. `cadex script --set`.
  4. `cadex params --set policy_on=1 --out runs/r3-rollout-seed0`.
- **Read:** checked the real trace's layout, then ran `docs/probes/ot9/runner/balance_eval.py` with the MJCF and task pins.
- **Regression:** `cli/tests/test_ot9_balance_eval.py` gained a test holding the r3 receipt to the contract pins, holding what ran to what was planned, and requiring the training seed to be outside the evaluation seeds. It also holds the rollout's policy sha to the stored policy, requires 401 frames for 400 steps, and marks seed 0 as a diagnostic.

## Result

- **Training is completed** (accounting class `completed`).
  - Exit 0 on gpu, 308.9 s. Bundle MJCF `933b1ac6` and task `1f8c1040` equal the pins.
  - Reward/step rose from ≈0.75 at iteration 26 to 0.9686 at the last iteration; best was 0.9836 at iteration 255. Final action std 0.251.
  - Trainer witness error 6.9e-8 against a 1e-4 tolerance.
  - Stored policy `r3-ppo-1.cxpolicy`, sha256 `ef71f370a2f189665f81f96026ba7281d73de332f0927cff7cf7a56944b0a94e`, 84,067 bytes, 5,634 parameters. Project commit `9175e4b`.
  - The curve is in `runs/r3-ppo-1/progress.json`.
- **Installed and engine-verified.**
  - Declare: accepted `cefc5898`, digest unchanged at `b933d905` (switch off), commit `301cd22`.
  - `policy_on=1`: accepted = working `df58d4ff825e3c029506fb661dfea18ef98e02b36f1894370241031578d21c96`, digest `6ff77527a39e22f4cbe985daeee6cbed4654aade80096ab0ab6ad4988b0ad96e`, commit `9e2bb4a`.
- **The trace layout matches the reader, so the reader is unchanged.** The trace has 402 frames: 1 untimed `input` frame plus 401 `solver_output` frames from 0.0 to 8.0 s at 0.02 s, for `step_count` 400.
- **Seed 0 (diagnostic only, not B3 evidence):**
  - Pass on the reader: 8.0 s, truncated, no `fallen`.
  - Peak tilt 5.35° at 0.06 s (the reset transient from 2.53°), then below 1° after about 0.2 s; at most 1.92° in the last 2 s.
  - Min chassis height 105.37 mm, against the 75.25 mm `fallen` threshold. Total reward 393.47.
  - Trace sha `6db76948…`. Policy, MJCF and task digests all match.
- **Tests:** `pixi run python -m pytest cli/tests` gave 930 passed and 1 skipped. The engine suite was not run because nothing under `src/` changed.

Concerns for the next iteration:
1. **Drift.** The policy balances while wandering: 838 mm of chassis xy displacement and a heading change over 8 s. The task rewards only alive and pitch, and the bar does not measure position. Report it; do not treat it as a failure.
2. **The trainer's `episode` figure is not an 8 s episode length.** It exceeds 400 late in training: 409.6 at the end, 1861.8 at iteration 295. Do not cite it as balance evidence.
3. **B2 is not complete yet.** It still needs a fresh-process reopen of `ot9-robin` showing the same policy and model identity, and the accepted policy has only been verified by the rebuild in this process chain.
4. **Rung 4 is next.** Run the frozen ten-seed evaluation, seeds 0–9, on accepted revision `df58d4ff`, with the README's loop into `eval/r3-ppo-1/seed-$S`, and report all ten.
5. The unreconciled tail now holds 3 records, so a reconcile is due by the charter's rule.

No new dependency. No policy binary or trace was committed; only digests.

Dispatch closed: 1 unit — first PPO run r3-ppo-1 (seed 1001, 300×1024, gpu, 309 s) completed on pinned artifacts, policy ef71f370 installed via the digest edit and engine-verified, real trace layout confirmed (401 frames), seed-0 diagnostic rollout passes the reader at 5.35° peak tilt.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot9
- commit: 34f310b593ff0d673404b6623eebdd158f09640f

## State Impact

- target: tidy-arbor-3203 — first offboard PPO run r3-ppo-1 completed on the pinned bundle (seed 1001, 300 it x 1024 envs, gpu 308.9 s, final reward/step 0.9686); policy r3-ppo-1.cxpolicy sha256 ef71f370 stored, declared by the digest edit and engine-verified at rebuild (accepted df58d4ff, digest 6ff77527); fresh-process reopen still outstanding (commit 34f310b5, docs/probes/ot9/retained/r3-robin-train-1.json)
- target: early-rain-5934 — the first real rollout trace confirms the reader's layout (401 solver_output frames for 400 steps); a diagnostic seed-0 rollout of ef71f370 runs 8.0 s with no fallen, peak tilt 5.35 deg, min height 105.4 mm, with ~0.84 m xy drift; the frozen ten-seed evaluation has not run
