---
node_id: 729a934b-b134-5641-97e2-71803b69bdf1
slug: green-delta-7130
title: 'cadex train/walk --remote: the remote-training handoff scripted, not run (ADR-200)'
created_at: '2026-09-06T19:44:53+00:00'
parents:
- shy-cabin-0798
summary: ''
---
## What

Scripted the lifecycle walk's remote-training handoff around `training/remote_train.sh` (ADR-089): `--remote` on `cadex train` and `cadex walk`. The train leg's command becomes `remote_train.sh train <bundle> <out> [--allow-cpu] -- <the same trainer flags>` in place of the venv's interpreter, and nothing else moves — the bundle and the model are exported into `DIR/train` as before (where the script looks for them, beside the bundle by name), the policy comes back to `DIR/train/<name>.cxpolicy`, the receipt is the same last JSON line, and the store, the digest edit, the verified rollout and `review.json` cannot tell the modes apart. New for both paths: the returned file is verified against the receipt's sha256, the box's path is kept under `training.trainer_out`, and a dispatcher `FAIL:` reaches the envelope's `error`. Landed with ADR-200, the `docs/CLI.md` §2 contract, a `training/SETUP.md` §d subsection, the §7c row 12 update in `docs/MUJOCO.md`, and a ROADMAP tick.

## Why

Target: `witty-spark-2613` (three modes, one shape), the plan's short unit 2 [rec: lone-wood-3732], as the overseer directed after unit 1 landed [rec: shy-cabin-0798]; serves mission 2. Assumptions made without a human: the remote leg trains **cold** — `remote_train.sh` copies two files out and the `--init-from` policy is not one of them, so a warm start with `--remote` is refused before any leg rather than failing on the box after a design turn spent tokens; carrying the pair is a change to the dispatcher and its own unit. `--detach` is not passed through: a walk waits for its leg, and a long run is dispatched by hand and continued from `cadex asset --put`, as SETUP.md already says. The CLI reads none of `.remote.env` and configures nothing, keeping ADR-089's fail-loud shape. The sha256 check runs on the local path too, because it cannot fail there and one code path is fewer than two.

## Method

Read `walk.py`, `command_train`, `command_walk`, `remote_train.sh`'s `cmd_train` (its argv contract, its model resolution, its printed shape: the trainer's stdout with MuJoCo's `warp` noise ahead of the receipt, then `==>` trailer lines) and SETUP.md §d. Split the trainer flags out of `trainer_command` into `trainer_flags` so the local and remote commands share one source; added `remote_trainer_command`, `verify_returned_policy`, and the stdout tail on a non-zero exit. Wired `--remote`/`--allow-cpu` into both parsers through one helper and one shared usage check. Tests: a stand-in `remote_train.sh` (bash, same argv contract, resolves the model the way the real one does, fails if it is not beside the bundle, prints the real shape, three failure modes by env var); the command pinned against the real script's usage line and against the local command (the tail after `--` is byte-for-byte the local flags); the returned-policy check through wrong bytes, nothing returned, and CPU fallback with and without `--allow-cpu`; the usage errors before any engine; `cadex train --remote --put` end to end against the real engine and the fake dispatcher; and the walk carrying the flags to the train leg only. Ran `test_train.py` + `test_walk.py`, then the full CLI suite with `JAX_PLATFORMS=cpu OMP_NUM_THREADS=1`.

## Result

**Scripted and verified offline:** `cli/tests/test_train.py` +3 and `cli/tests/test_walk.py` +1; the two files 30 passed in 87 s (real engine and trainer included); full `cli/tests` **134 passed in 111 s, no skips** (was 130). The end-to-end test shows the contract holds against the real export: `job-task.json` and `model-model.xml` land under `DIR/train`, the fake box finds the model where the real script would, the policy comes home under the same name and the store's sha256 is the receipt's. **Not executed:** no dispatch, no ssh, the GPU box's checkout untouched, no GPU run — the run's constraint, and ADR-200 says so; what a real box adds (reachability, the trainer-hash check, the device rule) is `remote_train.sh`'s and was not re-tested here. Not verified: no engine, shell or payload zone was touched, so no engine suite, build or packaged gate ran. Limits recorded: the remote leg is cold-run only; `--timeout` ends the local ssh, not the run. The unreconciled tail was two nodes on arrival and is three after this; the maintainer pass is due. Next, per the plan: short unit 3, the GUI-attached walk documented against the same project contract.

Dispatch closed: 1 unit — the walk's remote-training handoff scripted around remote_train.sh, offline-tested, never dispatched (ADR-200).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 5143099c602706e2f1e17cc1c9e0625aeb0d3867

## State Impact

- target: witty-spark-2613 — the remote mode is scripted: --remote on cadex train and cadex walk puts the train leg on the box through remote_train.sh with identical DIR/train artifacts, store, digest edit and review.json; offline-tested against a stand-in dispatcher and the real engine (134 CLI tests); not executed, cold runs only; GUI-attached mode still documentation-only and open
- target: calm-peak-5247 — the training leg has two homes behind one command: the venv's trainer or remote_train.sh, sharing one trainer_flags source; the returned policy is verified against the receipt's sha256 on both paths; a warm start with --remote is refused before any leg
- target: chilly-union-8972 — cadex train and cadex walk gain --remote and --allow-cpu (ADR-200); training.trainer_out carries the box's path; a dispatcher FAIL reaches the envelope's error
