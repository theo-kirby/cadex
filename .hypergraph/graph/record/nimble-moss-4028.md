---
node_id: 9fd10477-d4d3-5269-b055-7dfbf8e5322b
slug: nimble-moss-4028
title: cadex train and walk take the machine's training slot (ADR-543)
created_at: '2026-10-05T09:58:09+00:00'
parents:
- forest-jasper-1180
summary: ''
---
## What

`cadex train` now holds the machine's one training slot around a local
trainer, so `cadex walk`'s train leg does too (ADR-543, commit below). The
slot is the `~/.cache/cadex/training.lock` flock (`$CADEX_TRAIN_LOCK`) that
`loop.register`/`loop.supervise` already used.

- `loop.machine_slot()` is a context manager over that lock. It raises
  `LoopError(SLOT_BUSY …)` when the lock is held. `SLOT_BUSY` is now the one
  refusal sentence, shared by register, supervise and train.
- `command_train` refuses with exit 3 before its rebuild when the slot is
  held. It holds the slot only around `run_trainer`, not during the rebuild
  or the `put`.
- `command_walk` refuses with exit 3 before its first leg, so an iterate
  walk's sweep never moves the accepted revision for a run that cannot
  train.
- `--remote`, `train --dry-run` and `walk --complete` take no slot.
- `cli/tests/conftest.py` has an autouse fixture, `private_training_slot`,
  that gives every test its own lock file. The suite can then run beside a
  live job without being refused by it, and without holding the slot
  against it.
- Docs: a new paragraph in `docs/CLI.md` §5 and a sentence in §4's
  training-loop section. ADR-543 is in `docs/DECISIONS.md`.

## Why

The critic named this unit: the V2 baseline is blocked on the slot, which
is still held by the owner's `quad-qdd` `walk-r25` (iteration 441, trainer
ETA about 12770 s when this unit ended), and this unit needs no GPU.

**Deviation from the critic's message.** The critic asked for the walk's
train leg to go *through `loop.register`/`launch`/`supervise`*. I did not
do that. I made `cadex train` take the same lock instead. The reasons:

- Registration trains the task retained at the accepted revision, under
  `runs/<run>/`, with a budget and a reason, and it refuses evaluation
  seeds.
- The walk's train leg trains the bundle its own rebuild exports, into
  `--out/train`, after an optional sweep. It lands its own run record and
  `PROGRESS.md` row.

Re-hosting the leg would change the walk's artifacts and its tests. That is
a direction change, not a lock fix. The charter's rule is "one training
run, the lock is the arbiter", and that rule now holds on every local
path. ADR-543 records this deviation.

## Method

- Edited `loop.py` (adds `machine_slot` and `SLOT_BUSY`) and `__main__.py`
  (`command_train`, `command_walk`), and added the conftest fixture.
- New tests:
  - `test_walk.py::test_a_local_walk_or_train_is_refused_while_another_run_holds_the_slot`:
    with a fake lock held, `walk --set` runs no leg (the fake-leg log is
    never created), `train` is refused, and a `--remote` walk still runs.
    After release, the walk runs.
  - `test_loop.py::test_the_slot_is_one_lock_for_the_supervisor_and_cadex_train`:
    inside `machine_slot`, `register` is refused, a second holder is
    refused, and the slot is released afterwards.
- `test_loop.py::test_the_loop_names_no_behaviour` caught the word "walk"
  in my first loop.py docstring. I reworded the docstring and left the test
  as it was.
- Gates, all run with the GPU hidden (`CUDA_VISIBLE_DEVICES=`):
  - `pixi run test-engine`: 2585 passed, 58 skipped.
  - `pixi run python -m pytest cli/tests`: 1131 passed, 1 skipped
    (928.9 s).
  - No protocol or payload change, so the packaged gate was not needed.

## Result

True now:

- No local training on this machine runs outside the slot:
  - `train_start` runs hold it through the supervisor;
  - `cadex train` and `cadex walk` hold it around the trainer, and they
    refuse up front while it is held.
- The CLI suite can no longer be refused by a live training run, or hold
  the slot against one.

**Still open: the V2 baseline (short rung 3).** It has not been measured:
`walk-r25` still holds the slot. The next iteration should take it on
`orun3-biped` with seed 7 and `checkpoint_every` 10, timing iterations from
`progress.json` rewrite timestamps. It can now use `cadex walk` itself,
since the walk respects the lock. If the slot is still busy, it should do
P1's first cut (relative URLs), as the critic said.

**Note for the V2 watcher.** The watcher needs two call sites:
`loop.supervise`'s 0.25 s poll loop, and `train.run_trainer`, which today
blocks in `process.wait(timeout)` and would have to wait by polling. The
watcher itself should be one implementation called from both.

Tail: 3 unreconciled records including this one, so a reconcile is due by
the charter's rule.

Dispatch closed: 1 unit — cadex train/walk take the machine training slot (ADR-543), refused up front while held; tests isolated onto private slots; both suites green; V2 baseline still blocked by the owner's live run

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: 0c1b9cb83b72c7e25e8255073f5f08231168b312

## State Impact

- target: dry-rain-5997 — cadex train holds the machine training slot around a local trainer and cadex walk refuses before its first leg while it is held (ADR-543), so a walk leg can host the V2 baseline without sharing the 5090; baseline still unmeasured (owner's quad-qdd walk-r25 holds the slot); the checkpoint watcher will need call sites in loop.supervise's poll and a polling run_trainer.
