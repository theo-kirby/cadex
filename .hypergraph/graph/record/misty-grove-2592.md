---
node_id: e3df6e44-d938-52b8-820f-b0ec8af157e6
slug: misty-grove-2592
title: 'ot11 R1: --init-from carries the source policy''s exploration width (ADR-471, commit e6360889); recorded in iteration 76'
created_at: '2026-10-01T17:00:19+00:00'
parents:
- southern-rain-8433
summary: ''
---
## What

`--init-from` now continues a policy at the exploration width it trained to (ADR-471). `training/cadex_train.py` gains `starting_log_std(options, header, action_count)`, a pure, jax-free resolver. It returns `--initial-std` when the flag is given (warm or cold, source `flag`). Otherwise, on a warm start, it returns the source `.cxpolicy`'s per-action `exploration.log_std` (`init_from`), and otherwise 0.3 (`default`). `--initial-std` now defaults to unset. A warm-start source with no usable width (absent, wrong length, non-finite, or not pre-activation) is refused with a message naming `--initial-std`; it is not silently defaulted. The run's `init_from` provenance records `log_std_source`. A cold run's header still records `initial_std: 0.3`. The critic is not carried: the container holds none, and adding one would change the format the engine verifies.

## Why

This record is written in iteration 76, at the critic's request, for the unit iteration 75 landed as commit `e6360889` ("ouroboros #75: no record"): that iteration ended before it could record. The body below is iteration 75's draft, with its test line filled from iteration 76's runs.


The critic named this unit: "while r22 holds the GPU: the trainer fix … `--init-from` should carry the source policy's log_std, and its critic too if the .cxpolicy stores it, unless `--initial-std` is given explicitly". It serves **R1**. southern-rain-8433 measured that r20 and r21b lost r19's gait because a warm start reset σ from r19's 0.177 to 0.30 (and gave a fresh critic). Carrying the critic was not done because the `.cxpolicy` does not store one. That is the condition the critic attached.

The critic's other request, to fold the reconcile first, was **not done**. This dispatch forbids the reconcile skill in a work iteration. The tail is now 3 records (forest-rose-3078, southern-rain-8433 and this one), so a reconcile pass is due.

On "the frontier has not moved in 46 iterations": R1 remains the only open ot11 charter criterion the actor can move. This unit is pipeline work that removes a measured cause of R1's regressions. It does not touch the agent's task, reward or spec, or the r22 run.

## Method

- Read `train()`'s warm-start block, the header writer (`exploration.log_std`, ADR-103) and `cli/cadex_cli/loop.py`. The loop passes `--initial-std` only when the agent sets `initial_std`, so leaving it out now gets the carried width.
- Resolved `params["log_std"]` after the `--init-from` block, then retook the zeroed Adam moments, so the optimiser stays fresh.
- Tests in `cadex_tests/test_dynamics_policy_trainer.py`:
  - the flag is unset unless given;
  - the three-way resolution;
  - four unusable sources are refused, and the flag is the way through;
  - an end-to-end training-venv test: a cold run at σ 0.7, then `--init-from` with no flag, and the warm header's width is within 0.05 of the cold one's.
- Ran the new tests with the trainer change stashed: **6 failed, 1 skipped**, so they fail before the fix.
- Docs: ADR-471; `training/README.md` (date to 2026-10-01); `docs/CLI.md`; the agent's `train` tool description in `cli/cadex_cli/tools.py` now says a warm start keeps its source's width unless `initial_std` is set.
- GPU left alone: every test ran with `CUDA_VISIBLE_DEVICES=""` (`JAX_PLATFORMS=cpu` in the venv).

## Result

- **Fixed and tested.**
  - pixi, trainer file plus `training/`: 54 passed, 9 skipped (venv-only).
  - Training venv (`/tmp/trainer-test-venv`, CPU), the same files: **63 passed**, including the end-to-end warm-start test.
  - `pixi run test-engine` and `cli/tests` were **not run in iteration 75**, which ended before its record. They were run in iteration 76 on the ADR-471 tree (the next commit, `6babb356`, only touches the ot11 report, its receipts and `cli/tests/test_ot11_report.py`): `pixi run test-engine` (CPU) **2529 passed, 61 skipped**; the trainer test file re-run in iteration 76 gave pixi **38 passed, 9 skipped** and the training venv (`/tmp/trainer-test-venv`, CPU) **47 passed** in 224.9 s, the venv run including the end-to-end warm-start test.
- No engine, payload or protocol change, so the packaged gate is not needed.
- The in-flight r22 (`initial_std` 0.12, explicit) is unaffected.
- **r22's evaluation landed during this unit and was not published in it** (iteration 76 published it, commit `6babb356`). `r22-gentle-contact25` finished; its policy is e91a3970…, and it was evaluated at 2026-10-01 16:23:46 UTC: valid, **6 of 10**, failing W7 (2), W8-low (2), W2 (1) and W9 (1). The next iteration should publish it the way r21b was published: receipt, both ledgers, REPORT.md, and the `test_ot11_report.py` counts.
- Reconcile is overdue: the tail is 3 records.
- **Handoff — tried:** the r19 → r20/r21b/r22 warm-start line on ot11-quad-1, which reached 0, 2 and 6 of 10. **Would try next:**
  1. Publish r22.
  2. Let the agent's next warm start omit `initial_std`, so it continues at r22's own width under ADR-471. The agent decides; the actor does not tune it.
  3. If the walk still fails slip on a few seeds, carry the critic. That needs a `.cxpolicy` format change on both the trainer and the engine (a new ADR), so it is not a one-unit change.

Dispatch closed: 1 unit (iteration 75's, recorded in iteration 76) — `--init-from` carries the source policy's exploration width unless `--initial-std` is given (ADR-471), with a regression test that fails before the fix, run under pixi and the training venv

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 6babb356de9a5be78ecf0bc63d6e40ce2a7789a5

## State Impact

- target: late-pond-2851 — ADR-471 (commit e6360889): --initial-std defaults to unset; a warm start (--init-from) continues at the source .cxpolicy's per-action exploration.log_std unless --initial-std is given, refuses a source with no usable width, and records log_std_source; the critic and Adam moments stay fresh (the container holds no critic). Tests fail on the old source; test-engine 2529 passed, 61 skipped; trainer tests pixi 38 passed 9 skipped, training venv 47 passed including the end-to-end warm-start test. No engine, payload or protocol change
- target: smooth-fountain-9832 — the measured warm-start regression (r20, r21b reset sigma to 0.30 from r19's 0.177) has its width half fixed in the trainer (ADR-471); whether the width alone keeps a gait is answered against it by r22 (see the next record)
