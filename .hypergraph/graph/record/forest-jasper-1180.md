---
node_id: cf1fa1db-b947-5c46-af94-7c9870962902
slug: forest-jasper-1180
title: V2 baseline blocked by the machine lock; walk's train leg bypasses it; CLI.md stage paragraph fixed
created_at: '2026-10-05T09:31:20+00:00'
parents:
- snowy-lodge-1033
summary: ''
---
## What

Two things. First, the critic's doc fix: `docs/CLI.md` §`/api/project`'s
`stage` paragraph no longer describes the telemetry panel that ADR-533 removed.
It now says the page has no telemetry panel, that the ADR-542 overlay is drawn
from `/api/project`'s `stage` alone on the existing poll, and that
`/api/run/<name>` is fetched only when the 2D viewport plots a run's curve
(`review.js:494`). Second, an attempt at short rung 3 (the V2 baseline). It
was **blocked by the machine lock**, and what it found changes how the
baseline and V2 must be built.

## Why

These are the critic's two asks, in order. The doc fix was done as written.
The baseline run was **not** done, and here is why. When I checked, the 5090's
machine slot (`~/.cache/cadex/training.lock`) was held by a live owner run,
`quad-qdd/runs/walk-r25`: trainer pid 341422, 3000 iterations at 4096 envs,
budget 10800 s, about 28 min in, iteration 298, and the trainer's own ETA was
13800 s. The charter says the lock is the arbiter and nothing works around it.
The question policy says a capacity limit is not an attempt: keep the receipt
and wait. Waiting about 2.5 h idle inside one iteration is worse than handing
the next iteration a ready setup and a correction to the plan.

## Method

- Edited `docs/CLI.md`. The suites that grep `docs/CLI.md` (test_evaluate, test_project_docs, test_walk) passed with the GPU hidden: 123 passed in 389.85 s. The full suites were not rerun for this doc-only change.
- Copied `~/cadex-projects/ot5-biped` (14 MB) to
  `~/cadex-projects/orun3-biped` with `cp -a`. The source was not touched.
- Ran `loop.register(orun3-biped, run='baseline-probe', budget_s=1800,
  settings={iterations:120, seed:7, checkpoint_every:10})`. Receipt:
  `refused: another training run holds this machine's one training slot;
  wait for it to end.`, and `runs/baseline-probe` was not created.
- Ran `loop.retained_task(orun3-biped)`. It resolves task `reed_walk` at
  accepted revision `0596013572c6…`, with `evaluation_seeds: []`. So seed 7
  is legal, and the next iteration can register with no setup.
- Read `loop.supervise` (`cli/cadex_cli/loop.py:712`), `walk.run_leg`
  (`walk.py:299`) and `train.run_trainer` (`train.py:483`).

## Result

True now:

- `orun3-biped` exists as an untouched copy of `ot5-biped`, with runs
  `foot90`, `probe1..3` and the rest carried over.
- **No V2 baseline has been measured.** Short rung 3 is still open.

**A finding the next unit must act on: `cadex walk`'s train leg does not take
the machine lock.** The walk runs `cadex train` as a leg, and that leg reaches
`train.run_trainer` → `subprocess.Popen(trainer)`. Neither `walk.py` nor
`train.py` references `machine_lock_path` or `lock_held`. Only the MCP
`train_start` path does this, through `loop.register` → `loop.launch` →
`loop.supervise`, which takes `supervisor.lock` and the machine lock. So the
critic's "a `cadex walk` leg … going through loop.py's machine lock" names two
different paths. A `cadex walk` started now would have shared the 5090 with
walk-r25, which both breaks the one-run rule and corrupts any timing taken.

**Where the checkpoint watcher goes.** `loop.supervise` polls the trainer
every `POLL_S = 0.25` s, in the `while process.poll() is None:` loop at
`loop.py:765`. That loop already checks for a stop request and for the budget.
A watcher placed there would:

1. diff `loop.run_checkpoints(run)` (`loop.py:548`, every checkpoint file with
   its own sha256) against the ones already handled;
2. for each new checkpoint, start **one** sibling rollout process at a time
   (CPU engine, non-blocking `Popen`, never waited on inside the poll), which
   writes the `cadex-assembly-simulation-trace-v1` trace beside the
   checkpoint;
3. record a failure reason without ever affecting the trainer.

`train.run_trainer` has no poll loop: it blocks in `process.wait`. Putting the
watcher there would mean a second implementation. **Recommendation:** make the
walk's train leg run through `loop.register`/`launch`/`supervise`, so it gets
the lock and the watcher, or at minimum have `run_trainer` take the machine
lock. That is a one-unit change, recorded with an ADR. Take it before or
alongside the baseline, because B4 names `cadex walk` as the training path. The
interim alternative is to measure the baseline through `loop.register` +
`launch` on `orun3-biped`, which already holds the lock.

**Historical context, not a baseline.** These numbers come from the copied
runs' `progress.json` and use a different seed and settings:
`probe3` ran 240 iterations in 1003.7 s (≈4.18 s/iteration) with 23
checkpoints, so one every ≈10 iterations. `foot90` ran 240 iterations in
317.8 s (≈1.32 s/iteration). `progress.json` carries only the total
`wall_time_s`, not a per-iteration time, so the baseline's spread has to come
from timestamps sampled on `progress.json` rewrites or from the trainer's
stderr lines. The next unit should settle which source it uses before it runs.

**Plan for the next iteration.** When `lock_held(machine_lock_path())` is
false, register on `orun3-biped` with seed 7, `checkpoint_every` 10, about 120
iterations and a 1800 s budget, then measure. If the lock is still held, do
the walk-takes-the-lock unit first, since it needs no GPU.

Tail: 2 unreconciled records after this one, which is not yet fat.

Dispatch closed: 1 unit — CLI.md telemetry paragraph fixed; V2 baseline blocked by the owner's live quad-qdd run on the machine lock (refusal receipt kept); orun3-biped created; found that `cadex walk`'s train leg bypasses the machine lock; checkpoint-watcher site chosen in `loop.supervise`'s poll loop

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: f29dbb3535a06f2dd98499b3fb3a2853a50d310f

## State Impact

- target: dry-rain-5997 — No baseline yet: the 5090 slot was held by the owner's quad-qdd walk-r25 (refusal receipt kept). orun3-biped copied from ot5-biped, task reed_walk resolves with no evaluation seeds. cadex walk's train leg (train.run_trainer) takes no machine lock; only loop.supervise does, so the checkpoint watcher belongs in supervise's 0.25 s poll loop and the walk must route through loop or take the lock.
- target: vast-ivy-6277 — docs/CLI.md no longer describes ADR-533's removed telemetry panel; it describes the ADR-542 overlay reading /api/project's stage.
