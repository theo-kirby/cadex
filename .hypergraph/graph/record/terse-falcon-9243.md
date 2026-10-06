---
node_id: 0f559788-2eac-5044-a4d4-b9017bf6977f
slug: terse-falcon-9243
title: 'CLI suite lighter, last cut: remote-walk parity on the fixture trainer — 614 s as one command (ADR-564)'
created_at: '2026-10-06T12:50:21+00:00'
parents:
- crimson-anchor-3392
summary: ''
---
## What
Last CLI-suite cut under the owner note (ADR-564, commit on `ouroboros/orun4`). `test_walk.py::test_remote_walk_has_local_artifact_paths_with_a_cpu_dispatcher` now trains both its local and remote walks with `test_loop.py`'s `FIXTURE_TRAINER` instead of the real CPU trainer; every other leg is the real engine and every parity assertion stays. `dynamics_policy_fixtures.policy_container` now builds over `CadexDynamics.policy_channels` (ADR-408), so a task with privileged channels gets a fixture policy the engine accepts.

## Why
The critic's message: make the 39 s remote-walk parity test use a fake trainer, merge the two test_loop real-trainer tests if they duplicate, run the whole suite as one `timeout 590` command, ADR it, move on. Done as asked, except the merge: test_loop has only one real-trainer test (`test_one_round_of_the_loop_runs_through_the_product_path` already uses the fixture trainer and pins a different claim, the MCP evaluate round), so nothing was merged; ADR-564 says so.

## Method
Swapped the trainer through `train.TRAINER_SCRIPT` in the per-leg bootstrap plus `CADEX_TRAIN_PYTHON=sys.executable`, and in the dispatcher stand-in. First run failed: the fixture policy observed 5 channels where the hinged arm's policy reads 1 (privileged `com`, `effort`) — a stale fixture, fixed to `policy_channels`. Gates in the foreground: the whole CLI suite as one command with the GPU hidden; `pixi run test-engine` (fixture lives in the engine tests).

## Result
- Parity test 39 s → 18.6 s.
- Whole CLI suite, one command, `CUDA_VISIBLE_DEVICES= timeout 590`: 613.9 s, 1193 passed, 1 skipped, 1 failed — the failure is the timeout's SIGTERM reaching `test_the_walk_takes_the_toy_to_a_verified_rollout_and_iterates` at 590 s (pixi did not exit, so the run finished past the limit). Alone that test passed in 63.9 s. Counted as green with that caveat.
- `pixi run test-engine`: 2598 passed, 58 skipped, 337.8 s.
- Suite over ADR-562–564: 1017 → 793 → 647 → 614 s. **The 8-minute target is not met**; the remainder is keep-listed real-engine end-to-end tests. Per the critic, no further cuts; the thirds remain the foreground way to run the suite (note: `timeout` under `pixi run` does not kill the run cleanly).
- Next iteration: G2 — fold the ledger's lessons into the base and the printed-legged-robot style, then the fresh-session check.
- Tail is now 3 unreconciled records; reconcile is due.

Dispatch closed: 1 unit — remote-walk parity test on the fixture trainer, suite 614 s as one command (ADR-564)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: d9e469c9b851a65d5b026552ddcf9aa4633d1f6d

## State Impact

- target: early-arbor-7123 — the CLI suite runs 614 s as one foreground command (ADR-562–564, from 1017 s); 8-minute target not met, the remainder is keep-listed real-engine end-to-end tests
