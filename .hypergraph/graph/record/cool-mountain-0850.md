---
node_id: e730d5ce-1e64-52e4-b915-e00a37feef50
slug: cool-mountain-0850
title: 'ADR-576: the checkpoint stall measured and fixed — the witness rollout recompiled every snapshot'
created_at: '2026-10-06T22:35:04+00:00'
parents:
- golden-dune-2626
summary: ''
---
## What

ADR-576: the trainer's 37–39 s stall before each checkpoint, measured and fixed.
`snapshot` in `training/cadex_train.py` ran the witness rollout bare, outside the
jitted `iterate`, so its `jax.lax.scan` was compiled again on every checkpoint.
It is now jitted once (`witness_rollout = jax.jit(rollout)`).

## Why

This is the critic's named next unit: measure the stall (serialisation, eval
rollout, trace, fsync) before changing anything, then fix it with a failing-first
test and an ADR if one bounded step is the cause. It is a long-term rung of the
orun4 horizon ladder, an orun3 defect listed in REPORT.md §7.

**Deviation from the critic's message:** the critic asked for a hypergraph-reconcile
pass first, to fold `candid-walrus-1021` and `golden-dune-2626`. This iteration's
dispatch rules forbid reconcile in a work iteration, with no exceptions, so it was
not run. The tail is now three records (those two plus this one). That meets the
charter's three-unreconciled trigger, so the next iteration should be the
housekeeping reconcile.

## Method

- An instrumented scratch copy of the trainer, kept outside the repo, added
  `perf_counter` timings around `iterate`, `snapshot`'s rollout, the host copy,
  the witness, `policy_header`, `checked_policy` and `write_atomically`.
- It ran on the `orun4-biped-sts` copy's walk-r13 bundle with r13's
  hyperparameters, minus the warm start: 4096 envs, unroll 24, epochs 4, hidden
  256 128, `--checkpoint-every 2`, 7 iterations. The GPU was in use, under
  `flock -n ~/.cache/cadex/training.lock`, the machine lock.
- The compile count was taken with `JAX_LOG_COMPILES=1` on the swing-up fixture,
  for 3 and 6 iterations at `--checkpoint-every 1`, old trainer against new.

## Result

The stall is now fixed. Breakdown per checkpoint, before the fix:

| step | time |
|---|---|
| rollout | 42.5–45.4 s |
| host copy | 0.002 s |
| witness | ≤ 0.25 s |
| header | < 0.001 s |
| check and encode | 0.033 s |
| 176 KB write | < 0.001 s |
| one iteration, for scale | 1.9 s |

- **The cause:** a `best` checkpoint paid the stall twice. Old trainer: 6
  iterations compiled `jit(scan)` 16 times, 3 iterations compiled it 10 times.
  New trainer: `jit(rollout)` compiles twice in both runs.
- **After the fix,** on the same task: the first checkpoint takes 42.8 s (one
  compile), and later ones take 1.91–1.97 s. Seven iterations went from 274.0 s
  to 144.6 s of wall time.
- **The test:** `test_dynamics_policy_trainer.py::test_a_checkpoint_does_not_recompile_the_rollout`
  asserts that the compile counts for 3 and 6 iterations are equal. It fails on
  the HEAD trainer and passes with the fix.
- **The trainer test file:** in the training venv, 48 passed in 216 s. pytest
  came from a `--target` dir in /tmp, because the venv has no pytest. The
  venv is unchanged. Under pixi the test skips, like the file's other trainer
  runs.
- **Docs:** `training/README.md` notes the one compile. REPORT.md §7 and its
  ADR table are updated. The `docs/DECISIONS.md` entry carries the table.

**Gates** (all foreground, GPU hidden for the CLI suite):

- `pixi run test-engine`: 2611 passed, 59 skipped in 344 s.
- CLI third `NR%3==0`: 395 passed.
- CLI third `NR%3==2`: 489 passed.
- CLI third `NR%3==1`: 323 passed, 1 skipped, and 1 failed.
  - The failure was `test_review_checkpoints.py::test_both_scrubbers_keep_their_width_at_390px_in_either_theme[light]`,
    a browser layout check that this change does not touch.
  - Rerun alone, it passed twice (2/2). Its whole file then passed, 10/10.
  - It is recorded as a load-dependent flake and left alone, as the question
    policy says.

The trainer is not in any payload (ADR-084), so the packaged gate does not apply.

**Concern:** the bit-for-bit comparison with the old trainer is not exact, because
the GPU is nondeterministic run to run: best_reward at iteration 0 differs between
two runs before any snapshot, −0.926 against −0.922. The snapshot's rollout result
is discarded, as before, so the training trajectory is unaffected by design.

**Still open:** the `checkpoint_every` guidance defect, then reconcile, then claim
done. The tail now holds 3 records, so a reconcile is due.

Dispatch closed: 1 unit — ADR-576, the checkpoint stall measured (the witness rollout recompiled every snapshot, 42.5–45.4 s) and fixed by jitting it once; later checkpoints take 1.9 s.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 641f82834d63db7fe12f7e5c08c19ce5521c27b9

## State Impact

- target: late-pond-2851 — The trainer's checkpoint stall is fixed (ADR-576, commit 641f8283): snapshot's witness rollout recompiled its lax.scan on every call (42.5–45.4 s vs a 1.9 s iteration on a 4096-env biped); jitted once, later checkpoints take 1.9 s, pinned by a compile-count test
