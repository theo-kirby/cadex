---
node_id: 44b12892-6a3f-5995-a4f9-8a07026c300f
slug: amber-moon-0981
title: 'cadex train, the offboard trainer''s dispatcher, finished and recorded (ADR-191): §7c row 4 closes'
created_at: '2026-09-06T05:54:57+00:00'
parents:
- restless-harbor-4224
summary: ''
---
## What

`cadex train`, the dispatcher for the offboard trainer, finished and recorded (ADR-191). The code had landed in iteration 24 (commit `bb2513a0`, "session limit") with eleven tests and no ADR, no docs, no ROADMAP tick and no record node; iterations 25–49 all hit the session limit and changed nothing. This unit verified that code again, ran the leg for real, and wrote what was missing: ADR-191, `docs/CLI.md` (§2 table row and paragraph, §3 `training` envelope field, §4 overlay bullet, §8 limit), `docs/MUJOCO.md` §7c row 4 and frontier item 3, a ROADMAP tick, a pointer in `training/SETUP.md`, and the `__main__` docstring's seventh subcommand. Commit `38ed1777`.

## Why

The goal's item 1 (file lifecycle) is closed on `simple-willow-8989`; item 2's ordered frontier on `calm-peak-5247` names item 3, the `cadex train` dispatcher, as next after ADR-190. The overseer said the last iterations changed nothing and to pick a rung with items; this rung was half-done and unrecorded, so finishing it was the smallest unit that moves the frontier and leaves nothing invisible. Assumption made without a human: the ADR number is 191, because the code's docstrings already cite it and nothing else claims it. Not taken: a tool that lets the model turn spawn the trainer — the agent has no shell and a fifteen-minute subprocess inside a turn is the wrong shape; the leg is the caller's or a pipeline's, one command, and the overlay says so.

## Method

Read `cli/cadex_cli/train.py`, `command_train` and the parser in `__main__.py`, the `report.py`/`agent.py` diff from `bb2513a0`, `test_train.py`, the trainer's parser, and the doc slots. Ran `pixi run python -m pytest cli/tests` with the built engine present. Copied `~/cadex-balance-ns` to `/tmp/nt1-train-scratch/proj` (never the live project) and ran `./cadex train --iterations 2 --envs 8 --put --timeout 600 --json`. Wrote the docs and ADR from the code, bumped `training/SETUP.md`'s verified date, committed, re-ran `test_train.py` and `test_commands.py` after the docstring edit.

## Result

- `cli/tests`: **103 passed** in 46.3 s, engine present, nothing skipped; the real-trainer test (1 it × 4 envs) included. After the doc edits `test_train.py` + `test_commands.py`: 27 passed.
- The leg on the scratch copy: exit 0, **18.5 s** wall; trainer `wall_time_s` 3.7 s on `cpu`; task digest `602d62c1…` equal to the audit's; 28 053 bytes stored as `balance_task.cxpolicy`, sha256 `1e0801aa…` identical in the receipt and the `assets` row; `--out` held the bundle, the policy, its `.best` checkpoint, STEP and STL. Reward/step −0.95 after two iterations, as expected for an untrained toy.
- §7c row 4 closes; legs 3 → 7 are one command plus `cadex script --set`. Item 4, the iterate shape, is next; item 5 (`INSPECTION_FAILED` frame) and item 6 (project scaffold) untouched.
- The unreconciled tail is now two nodes (`restless-harbor-4224` and this one); the last reconcile failed on the session limit and a maintainer pass is owed.
- Not chased: every `cadex train` export leaves a fresh attempt directory, same as `cadex export`.

Dispatch closed: 1 unit — `cadex train` documented and recorded (ADR-191); §7c row 4 closes, cli/tests 103 passed, the leg run in 18.5 s on a scratch copy.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: 38ed1777b12ba5f4b13c04286fb971bc4fd924d8

## State Impact

- target: calm-peak-5247 — §7c row 4 (training) closes: cadex train --out DIR --iterations N --envs N --put rebuilds, exports the bundle, runs training/cadex_train.py under the training venv with flags pinned by name and test-read from the trainer's parser, and stores the policy with its sha256 in the envelope (ADR-191); the code landed in iteration 24 (bb2513a0) unrecorded and is now documented; measured 18.5 s wall for 2 it × 8 envs on a scratch copy, task digest 602d62c1… equal to the audit's; legs 3→7 are one command plus cadex script --set; frontier item 3 done, item 4 the iterate shape is next; the agent itself still has no shell, so the leg is the caller's or a pipeline's by decision
- target: chilly-union-8972 — a seventh subcommand, cadex train (--iterations, --envs, --seed, --label, --init-from, --task, --name, --put, --timeout, --trainer-python); training is a new optional envelope field carrying the trainer's receipt as printed; the interpreter is --trainer-python, $CADEX_TRAIN_PYTHON, <repo>/.venv, ~/cadex-train-venv and is never created; cli/ depends on training/cadex_train.py by path and on its flag names by test, and training/ stays out of every payload; cli/tests 103 passed
