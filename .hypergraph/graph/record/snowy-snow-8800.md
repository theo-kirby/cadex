---
node_id: 6bf6a23b-432b-5a5b-b6fa-7acae6b0d7be
slug: snowy-snow-8800
title: 'ot11 grip: ADR-474 coupled goal followers placed by their law (record backfilled for #90)'
created_at: '2026-10-01T20:41:33+00:00'
parents:
- blue-cloud-1514
summary: ''
---
## What

Iteration #90 landed ADR-474 (commit `ebd6640c`) and stopped without a record. This node is that record, written by iteration #91 from the commit itself.

ADR-474: a point goal on a coupled mechanism now places every gear, belt or screw follower by its coupling law before it judges the pose.
- `src/Mod/cadex/CadexDynamics.py`: a point goal's record carries `followers` (one row per active `equality/joint`: follower and driver `qpos` addresses, both references and the five `polycoef` terms). `_place_goal_followers` writes `reference + Σ c_k·x^k` with `x = qpos[driver] − driver_reference` after the drawn joints and before `mj_forward`. `GOAL_FOLLOWER_ALGORITHM` is appended to `goal_algorithm` only on coupled models.
- The same lines in the reference runner (`cadex_tests/dynamics_task_episode.draw_goals`) and the trainer (`training/cadex_train.py`, `place_goal_followers`).
- `cadex_tests/test_dynamics_goal_coupled.py` (new): the probe gripper rebuilt headless; the follower record; the law's equality residual is zero on the 1:1 gripper and the 2:1 M2 gear train; the draw test run against all three implementations; the three draws agree on a coupled mechanism.
- `docs/DECISIONS.md` ADR-474, `docs/XSCRIPT.md`, `docs/probes/ot11/README.md`, `training/README.md`.

## Why

The critic's message for #91 asked for this record first, with its impact on `salty-isle-4063` and parented on `blue-cloud-1514`, because the unit #90 did is invisible to the project until it is recorded. ADR-474 itself closes the first of the two gaps `blue-cloud-1514` measured (the goal draw ignored couplings).

## Method

- Read commit `ebd6640c` and ADR-474.
- Re-ran the engine suite at that revision, in a clean worktree of `ebd6640c`, CPU-only.

## Result

**What is true at `ebd6640c`:**
- The goal draw places coupled followers by the coupling law in the engine, the runner and the trainer. Its draw test fails on the old source at exactly `{(1102, 1), (1105, 1), (1110, 1)}`, the targets whose coupled jaws overlap by 0.5–4.3 mm, and passes on the new one (ADR-474's own receipt).
- Uncoupled bundles, their digests and every policy naming one are unchanged.
- Engine suite at `ebd6640c`, worktree with no build: 2378 passed, 222 skipped, 0 failed. The skips are the engine-needing tests, which skip without a built engine in that tree; the full-build receipts are in the next record.

**Not done by #90:** a record, the cli suite and the packaged gate. #91 ran the suites and the gate at its own revision, which contains this change.

**Open after ADR-474:** coupled jaws had no contact (joint-pair exclusion covered couplings), so the three targets were read correctly and still accepted. And MJX 3.10's handling of `equality/joint` was unmeasured.

Dispatch closed: 1 unit — backfilled record for ADR-474 (coupled followers placed by their law in the goal draw), with an engine-suite receipt at its revision

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: ebd6640c52fc67818f5d32b593bcfa08a9c446c0

## State Impact

- target: salty-isle-4063 — A point goal on a coupled mechanism places each gear, belt or screw follower by its coupling law before judging a pose (ADR-474, commit ebd6640c), identically in the engine, the reference runner and the trainer; uncoupled bundles and digests unchanged. Regression fails on the old draw at exactly 1102/1105/1110 segment 1 of the frozen grip-probe seeds.
