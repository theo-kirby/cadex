---
node_id: 862eb031-4079-5ea3-8289-63b319cad684
slug: idle-falcon-3004
title: A warm start travels to the remote box
created_at: '2026-09-08T22:08:54+00:00'
parents:
- western-cliff-6876
summary: ''
---
## What

A warm start now travels to the remote box. `training/remote_train.sh train`
lifts `--init-from` and `--init-from-parent-task` out of the flags after `--`,
copies both files into a `warm/` subdirectory of the run directory, and
re-emits the two flags pointing at the copies; the CLI's `--remote` refusal is
gone. ADR-268, `docs/ROADMAP.md`, `docs/CLI.md` §2, `training/SETUP.md` (d),
`docs/MUJOCO.md` §7 row 12 and the project-doc scaffold in the same commit.

## Why

The charter's **Three modes, one shape** criterion is on the frontier, and its
remote limb was the one place the modes were *not* one shape: ADR-200 refused a
warm start with `--remote` before any leg ran, because the dispatcher carried
two files and the curriculum pair (ADR-161) is two more that name paths on the
dispatching machine. That made *iterate* — the second half of the lifecycle
loop and its own ticked criterion — a local-only operation. `witty-spark-2613`
carried this as declared negative knowledge ("a warm start with `--remote`:
refused before any leg … carrying the pair is a change to the dispatcher and
its own unit"), which is exactly the unit the overseer asked for: one script
under `training/`, dispatch only, ADR-089's shape, scripted and not executed.

Assumption written down rather than asked: the dispatcher rewrites the paths,
not the CLI. Transport is the script's job, so `remote_trainer_command` still
builds the local trainer's flags byte for byte in both modes and the identity
the tests pin is unweakened.

## Method

- The parse loop after `--` captures the two path-valued flags instead of
  passing them through; existence, and a basename collision that would clobber
  one file with the other in a flat `warm/`, are checked before the box is
  contacted; the joined `--init-from=PATH` form is refused because its path
  would reach the box unrewritten.
- The copy and the rewrite happen before the `--detach` branch, so both the
  blocking and the detached path get them.
- `cli/`: the `TrainError` in `remote_trainer_command` and the usage error in
  `_remote_usage_error` are removed; `train --dry-run`'s plan names the warm
  files in `artifacts` and in the `copy-out` step, in **both** modes, derived
  from the built command (`warm_start_files`) rather than passed in beside it.
- Evidence against the **real** script for the first time on this leg: a `box`
  fixture puts stand-in `ssh` and `rsync` on PATH so this filesystem is the
  box, and `bash training/remote_train.sh train` really parses, copies and
  re-points. The stub splits the trainer line the way the remote shell would.
- Two tests that pinned the old refusal (`test_train.py`'s usage-error table,
  `test_walk.py`'s remote walk) now pin the new behaviour: the triple reaches
  the train leg beside `--remote` and no other leg, exit 0.

## Result

`pixi run python -m pytest cli/tests`: **258 passed, 0 skipped, in 3:48**. The dispatcher's own
tests: warm start carried (both files byte-identical in `warm/`, the
re-pointed flags are what the trainer is handed, the local paths do not
travel, bundle and model still flat beside them, policy home verified) and
three refusals that exit before the trainer is reached. `bash -n` clean; bash
3.2 constraints respected (no associative arrays, no `${x@Q}`, no apostrophes).

No dispatch, no ssh to any machine, no `.remote.env` read, no engine, protocol,
payload or `shell/` diff; `training/` still enters no CMake rule, no payload
and nothing in `pixi.toml`.

Charter criterion advanced: **Three modes, one shape** — the remote limb's last
declared shape difference is closed, so an iterate is the same operation in both
modes. Still missing before the criterion can be ticked by a human: nothing
under this run's constraints (the GUI mode is documented and the remote mode
scripted, both deliberately unexercised) — what is genuinely unproven is a real
dispatch to a real box, which those constraints forbid. `--detach` still does
not travel through the CLI's walk, and that remains its own unit.

Three record nodes were already unreconciled before this one; this makes four.
The tail is fat and a maintainer pass is due.

Dispatch closed: 1 unit — the remote dispatcher carries a warm start out and
re-points it, so an iterate has the same shape locally and on the box.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 2addc0b33c049bfd3c20d1efb09d38ff2712791b

## State Impact

- target: witty-spark-2613 — the remote limb's last declared shape difference is closed: remote_train.sh carries --init-from's policy and --init-from-parent-task's bundle into the run directory's warm/ and re-points the flags (ADR-268), so an iterate is the same operation locally and on the box; the CLI's --remote warm-start usage error is gone and train --dry-run names the warm files in both modes. Tested against the real script with stand-in ssh/rsync; cli/tests 258 passed 0 skipped. Still not executed: no dispatch, no ssh, and --detach still does not travel through the walk
- target: calm-peak-5247 — the walk's iterate leg is no longer pinned to this machine: cadex walk --remote with the curriculum triple reaches the train leg and no other, verified against a stand-in dispatcher
