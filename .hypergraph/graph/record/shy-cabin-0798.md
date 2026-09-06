---
node_id: ecb30d47-c206-5d69-b8f7-149996ff34cd
slug: shy-cabin-0798
title: 'cadex walk qualified on the toy: review lands in the project, 13 tests, ADR-199'
created_at: '2026-09-06T19:32:55+00:00'
parents:
- lone-wood-3732
summary: ''
---
## What

Qualified `cadex walk`, the one-command lifecycle entry point that d34c3cab carried untested and undocumented, on the repository's plate-and-arm toy, and fixed forward the two gaps the real run showed. Landed as a4248b26: `review.json` under `--out` as the walk's own artifact and commit, checkpoint and trace hygiene in the scaffolded project `.gitignore`, `cli/tests/test_walk.py` (13 tests), ADR-199, the `docs/CLI.md` walk section, the ROADMAP tick and a §7c note in `docs/MUJOCO.md`.

## Why

Target: `crisp-reef-5607` (the walk exists and is tested headlessly), the plan's short unit 1 [rec: lone-wood-3732], serving mission 2. The audit [rec: fond-mesa-1562] proved the legs but not a single documented entry point: its helper supplied the digest edit, its outputs sat beside the project, and nothing reviewed into the project. Assumptions made without a human: the store's `assets/*.cxpolicy` stays committed (ADR-194 says the stored assets are the project) while the trainer's checkpoints, the copies in a run's `train/` and the `*-trace.json` rollouts are ignored, because the plan says to commit numbers and never checkpoints or traces, and the file is editable per project; the domain-doc convention is exercised by the caller (the real test writes `docs/sensors.md` and the walk's legs commit it) rather than generated, because a generated doc is a new tool and the charter prefers a convention first; no `--prompt` in the real qualification, because the toy is repo-owned and a turn would spend tokens for nothing.

## Method

Read the walk implementation, the audit record, the iterate test and the project-docs module. Seeded a scratch project outside the repo from the test's `ITERATE_SCRIPT` with a placeholder digest and ran `cadex walk --iterations 1 --envs 4 --timeout 600` under `--out <project>/runs/walk-1`, then the iterate walk with `--set lift_weight=2e-4 --name job2.cxpolicy` and the warm-start triple. Inspected `PROGRESS.md`, `git log --stat` and `git ls-files` in the project. Added `write_review` to `walk.py`, wired it into `command_walk`, let `_commit_run` commit the walk (it skipped it before), and extended the `.gitignore` template. Wrote the test file in three layers: string-level digest edit and review reader; orchestration against a fake `cadex` script that answers each leg in envelopes and logs argv; the toy through both real walks with the real engine and trainer. Ran the file, then the full CLI suite with `JAX_PLATFORMS=cpu OMP_NUM_THREADS=1`.

## Result

Both pre-change walks exited 0: 15.5 s and 16 s wall, `total_reward -27.1094` then `-55.3480` with `Δ -28.2 vs 2c1ad3fb at -27.1` in the project's `PROGRESS.md`, eight project commits — the audit's numbers exactly. Gaps shown and fixed: the review lived only in the stdout envelope; the `train` leg's commit carried `job.cxpolicy`, `job.best.cxpolicy` and the store copy, three copies of one policy. After the change: `cli/tests/test_walk.py` 13 passed in 31.8 s (real engine and trainer included); full `cli/tests` 130 passed in 111 s, no skips. The real test asserts the walk's commit is last, `runs/*/review.json`, `assets/*.cxpolicy` and `docs/sensors.md` are tracked, and no `.cxpolicy` outside `assets/` and no trace is. Not verified: no engine or shell zone was touched, so no engine suite, build or packaged gate ran; no GUI, no remote dispatch, no agent turn. Not done, as the charter's own items: the second mechanism, the GUI-attached doc, the remote handoff script. The `.gitignore` decision is reversible per project. The unreconciled tail was one node on arrival and is two after this.

Dispatch closed: 1 unit — `cadex walk` qualified on the toy, review lands in the project, tests and ADR-199 landed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: a4248b2610a8dae94255886b18e80694d835e80b

## State Impact

- target: crisp-reef-5607 — cadex walk is the documented headless entry point, qualified on the repo-owned toy through two real walks (placeholder digest to verified rollout, then a reward change with a warm start); review.json lands in the project; checkpoints and traces stay out of its history; second mechanism, GUI and remote modes remain open
- target: calm-peak-5247 — the digest edit is the walk's (a two-literal rewrite of the one assembly.policy call); the walk commits its review.json; cli/tests/test_walk.py pins leg order, flags, refusals and the real toy walks; full CLI suite 130 passed
