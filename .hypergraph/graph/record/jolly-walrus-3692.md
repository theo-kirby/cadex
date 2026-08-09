---
node_id: a92f72cc-7fbf-5196-a225-14cbedc223da
slug: jolly-walrus-3692
title: 'Prehistory: the 07-31 spike — a headless CLI, and training moves to a GPU box'
created_at: '2026-08-09T15:16:12+00:00'
parents:
- merry-eagle-4093
- sage-wood-0687
summary: 'The busiest day in the repo: cli/ and training/ both born, plus remote dispatch to a cloud GPU box. No engine change and no protocol change.'
---
## What

51 commits in one day — the busiest in the repository's history. Two top-level
directories were born on it: `cli/` (ADR-061) and `training/` (ADR-084), plus
remote dispatch shortly after (ADR-089). Per the author, it was simply a day
with a lot of time, spent banging on several things at once: the wiring side, a
headless CLI, and standing up the remote training environment.

## Why

Branches from the merge era and from the MJC arc. The CLI is new scope that no
phase declared; `training/` is the direct consequence of M7 deciding that
training happens elsewhere.

## Method

**`cli/`** is a second *front end* and a third client of the same protocol: no
Blender, no display, no shell code, four subcommands (`-p`, `params`, `script`,
`export`) of which exactly one spends tokens. Its whole model-facing tool surface
is **generated from `OP_ARG_SPECS`**, so it cannot drift from the contract it
drives. It is LGPL, and the licence boundary against the GPL `shell/` is one-way
and hard: copying a line of the shell's client into `cli/` relicenses the engine
side and is not a judgement call.

**`training/`** is the one top-level directory that is deliberately *not part of
the product*. CMake never installs it, no payload carries it, nothing in it
enters `pixi.toml`, and it cannot import Cadex — it reports whether
`CadexDynamics` was importable so a test can assert the negative. Its four
dependencies (`jax`, `mujoco`, `mujoco-mjx`, `flax`) are exactly pinned in
`training/requirements.txt` and installed into a venv **on whatever machine
trains**.

**The machines, which nothing in the repo states.** Development happens on the
author's MacBook and Mac mini. Training happens on a **cloud server with a
GPU**. `training/remote_train.sh` dispatches a run there; results come back by
rsync and are viewed locally — later, in live mode.

## Result

The CLI cost **no engine change and no protocol change**: `OP_ARG_SPECS`, the
ADR-027 goldens and `docs/INTEGRATION.md`'s op table are untouched. That is the
point — a third client that needed the contract widened would have been evidence
*against* the contract, and instead it is the first direct evidence for the
Phase 11/12 claim that either half is replaceable.

`remote_train.sh` refuses a run that silently fell back to CPU, and a box whose
pinned versions do not match, because both otherwise show up only as a number
nobody compares. ADR-098 later found two silent bugs in it: `train.pid` held the
wrapping subshell rather than the trainer, so `stop` reported success while a
4,000-iteration run carried on; and `shquote` mis-escaped embedded single quotes
under bash 3.2.

**Known and deliberate gaps in `cli/`**: it has never been run on macOS by hand;
export runs as a `FreeCADCmd` subprocess rather than an `export_model` op; BREP
outputs only, with mesh and component outputs reported `skipped`; no
`resolve_pin` and no offscreen rendering; it does not ship inside the engine
payload; Windows is unsupported.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: NEW cli — a third protocol client with no display and a generated tool surface; verified on Linux, unverified on macOS.
- target: NEW rl-training-loop — training is offboard on a GPU box, dispatched by script and pulled back by rsync.
