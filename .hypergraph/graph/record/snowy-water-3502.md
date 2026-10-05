---
node_id: 1c8f3b11-9805-5e85-ae51-dac58cd63ef3
slug: snowy-water-3502
title: 'V2: each checkpoint rolled out through the engine while training (ADR-544), cost and disk measured'
created_at: '2026-10-05T11:24:36+00:00'
parents:
- nimble-moss-4028
summary: ''
---
## What

V2's first half: rolling out each checkpoint, plus the cost and disk measurements V2 requires (ADR-544, commit `025417e7`).
- `cli/cadex_cli/checkpoints.py` has one watcher, `CheckpointRollouts`. Two places poll it: `loop.supervise` (behind `train_start`) and `train.run_trainer` through a new `on_poll` hook (behind `cadex train`, and so behind `cadex walk`'s train leg).
- Each new numbered checkpoint `<out>.<tag>.cxpolicy` is played by `checkpoint_runner.py`. The runner runs under the engine's interpreter, on the CPU, `nice`d, one checkpoint at a time, newest first. It writes `<out>.<tag>.rollout-trace.json` (`cadex-assembly-simulation-trace-v1`, with a `checkpoint` block: file, tag, iteration, reward_per_step, sha256). If the rollout fails, it writes `<out>.<tag>.rollout-failed.json` with the reason instead.
- `cadex train` and `cadex walk` gain `--checkpoint-every N`.

## Why

The critic named this unit: a V2 checkpoint watcher, written once and called from both supervise and a polling run_trainer, tested with orun3-biped fixture checkpoints and a real engine, with disk bytes per trace measured, ADR-544 and a record. The critic also asked for the no-rollout baseline once the slot freed. The slot was free during this iteration (`lock_held` False, GPU idle). So I took the baseline and, in the same session, the on-vs-off comparison V2's cost bullet needs.

What differs from the brief: the baseline was not a `cadex walk` leg on the `orun3-biped` project. It was the same trainer command `cadex train` builds, run through `run_trainer` under `machine_slot()`, on a copy of orun3-biped's own `reed_walk` bundle in `/tmp/orun3-biped-v2cost/`. Reason: a walk would rebuild the project and store policies into `orun3-biped` for a timing measurement. Iteration time is the trainer's alone either way.

## Method

- Runner checked by hand on `orun3-biped/runs/probe3`'s 11 real checkpoints (copied to /tmp): 11 traces in 1.8 s, 0 failures, component names equal to the walk rollout trace's `*_link` names.
- Tests: `cli/tests/test_checkpoint_rollouts.py`, 7 tests, against the resolved engine, with no skips. The fixture is the biped's model and task bundle (`cli/tests/fixtures/orun3-biped/`). Checkpoints are generated with the engine suite's `dynamics_policy_fixtures.policy_container`, because policy binaries are never committed. A fake trainer waits for each checkpoint's trace before going on. That proves rollouts land during training through both `run_trainer` and the detached supervisor.
- Cost harness `/tmp/orun3-biped-v2cost/measure.py`, not committed. It ran on the RTX 5090: 60 iterations, 256 envs, seed 7, `--checkpoint-every 5`, in the order off, on, off, on. Each iteration's time was taken from the stderr timestamps of `iteration N` lines, for N ≥ 2.
- Suites: `pixi run python -m pytest cli/tests` with the GPU hidden gave 1138 passed, 1 skipped. Then the doc, train and loop tests were rerun after the doc edits: 458 passed, 1 skipped. `pixi run test-engine` gave 2585 passed, 58 skipped.

## Result

What is true now:
- Rollouts run while training continues, with **no measurable cost**.

  | run | mean s/it | median s/it |
  |---|---|---|
  | off-1 | 9.435 | 0.9166 |
  | on-1 | 9.045 | 0.9176 |
  | off-2 | 9.061 | 0.9170 |
  | on-2 | 9.068 | 0.9169 |

  Taking each on-run against the off-run before it (on-1 vs off-1, on-2 vs off-2): mean −4.1 % and +0.08 %, median +0.11 % and −0.01 %. Under the 5 % bar.
- All 22 rollouts were written. **Disk**: 38.7–329.5 KB per trace (size follows episode length; a full 8 s horizon at 25 fps is 329.5 KB). Mean 224.7 KB per checkpoint, 2.47 MB for 11.

Concerns for the next iteration:
- The mean iteration time is about 10× the median because a few iterations stall for tens of seconds (about 460 s per run), with rollouts on or off. Which iterations stall was not recorded.
- Same-seed GPU runs produce different policy digests.
- V2 is still open on the page side: a playback route through `trace_playback`, the viewport looping the newest checkpoint, the scrubber, a browser test against a real engine while a run trains, and the failure reason shown on the page. The route also enters P1's contract once that exists.
- The first measured pair (off-1/on-1) includes first-run warm-up. The later pair is the clean comparison.
- Remote checkpoints are not rolled out.
- No new dependency.

The tail now has one unreconciled record.

Dispatch closed: 1 unit — V2 checkpoint rollouts during training (ADR-544), measured no cost and 224.7 KB/trace on the biped

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: 025417e7287da98d8b5e0671333f0d60ec09ab65

## State Impact

- target: dry-rain-5997 — Checkpoint rollouts land during training through one watcher in both supervise and cadex train/walk (ADR-544, commit 025417e7); measured on the biped on the 5090: no measurable iteration-time cost (median 0.9169-0.9176 s/it on vs 0.9166-0.9170 off), 224.7 KB mean per trace, 2.47 MB per 11 checkpoints. Page playback, scrubber and live browser test still open.
