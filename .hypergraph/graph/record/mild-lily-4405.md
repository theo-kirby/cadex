---
node_id: 677771c3-721f-5dbc-a118-404a479b76df
slug: mild-lily-4405
title: 'ot10: ADR-433 survival read as trailing-window median; w2-2 re-reviewed walked=true, w2-1 still false'
created_at: '2026-09-28T17:11:29+00:00'
parents:
- kind-loom-7489
summary: ''
---
## What
ADR-433 (commit on `ouroboros/ot10`): `cadex walk`'s gait check (`cli/cadex_cli/walk.py::_training_survival`) now reads training survival as the **median of the stored `episode_steps_curve` samples over the last 50 iterations** (`SURVIVAL_WINDOW`), each capped at the horizon, instead of the last iteration alone. The 0.90 bar (`SURVIVAL_FRACTION`) and all other gait thresholds are unchanged. Then `w2-1` and `w2-2` on `~/cadex-projects/ot10-quadruped-3-w2` were re-reviewed from their stored review inputs.

## Why
The critic's message asked for exactly this unit: fix the survival measurement in its own unit, with a reader that works on stored curves (they carry no `terminals` field and no unroll), as an ADR stating it is a measurement correction with the 0.90 bar unchanged, a regression test built on w2-2's curve shape that fails on current source, then re-review both runs and publish both verdicts. Done as asked; I chose the trailing-window option (median) over horizon-boundary skipping because the unroll is not in the progress file the gait check reads. Serves W2 (`golden-garden-8501`).

## Method
- Trainer's figure is `unroll*envs/endings` with truncations counted (`training/cadex_train.py:1647`); with unroll 20 / horizon 500 every 25th batch is a boundary; iteration 999 always is.
- Median chosen over harmonic mean: the stored curve keeps 512/1000 iterations, so the harmonic mean swings with whether a boundary sample was kept (w2-2: 315 over last 50, 506 over last 100).
- Tests in `cli/tests/test_walk.py`: `test_survival_is_not_read_off_a_horizon_boundary` (w2-2 shape, steady 1107 / boundary 31.9 → survives, walked) and `test_a_run_whose_episodes_really_end_early_still_fails_survival` (steady 30 and 440 → fails with new finding). Both fail on the pre-change source (stash check: 2 failed, 70 passed); with the change `test_walk.py` + `test_ot10_contract.py` 93 passed.
- Re-review: `gait_from_trace` on each run's stored trace, model XML, task bundle and `train/progress.json`; every non-survival gait field compared equal to the stored `review.json`. Written to `runs/<run>/gait-adr433.json` in the project copy (not git).
- Cross-check with the unroll recorded in the policy header (20) and 2048 envs: total steps / total endings across the two full horizon periods 950–999.

## Result
- `w2-1`: survival median 487.6/500 (0.975) passes (was 213.3 at iteration 999); still **walked = false** — tipped at 4.36 s, terminated at step 218.
- `w2-2`: survival median 500/500 (1.00) passes (was 31.9); no findings; **walked = true**. Cross-check mean episode 489.5 (w2-1 485.5), so not an artefact of the cap.
- W2's bar (`walked = true` on one A5 design with the unchanged ADR-410 overlay, `--stop-on-collapse`, pre-registered settings, supported install, W1 video and curve published) now has evidence from `w2-2`; the owner ticks it. `w2-2` was a warm start from `w2-1` on a byte-identical task bundle, as pre-registered.
- Docs: ADR-433 in `docs/DECISIONS.md`, `docs/CLI.md` gait paragraph, `docs/probes/ot10/README.md` re-review section.
- Not run: full `cli/tests` and `pixi run test-engine` at this revision (only `test_walk.py` and `test_ot10_contract.py`); C1 still needs both at the final revision. No engine/payload change, so no packaged gate needed.
- The stored `review.json` files were left as written; the corrected verdict lives in `gait-adr433.json` beside each. Future `cadex walk` runs write the new block directly.
- Next suggested: the trainer could count true terminations separately (future runs), but that is not needed for W2. Tail is 3 unreconciled records now — reconcile due.

Dispatch closed: 1 unit — ADR-433 survival measurement correction; w2-2 re-reviewed walked=true, w2-1 still false

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 03aaeb917f6f17c2a8dd98c1d1f00fc994b1838e

## State Impact

- target: golden-garden-8501 — W2 has walked=true evidence: w2-2 on ot10-quadruped-3 re-reviewed under ADR-433 (survival median 500/500 over iterations 950–999, bar 0.90 unchanged; cross-check 489.5), no findings; w2-1 stays walked=false (tipped 4.36 s)
- target: calm-peak-5247 — the walk's gait check reads training survival as the median of the last 50 iterations' episode lengths (ADR-433), not the last iteration, which can close on a horizon boundary
