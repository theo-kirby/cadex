---
node_id: 47091e8e-f501-57ab-b7c7-afda1b9d98b0
slug: rustic-bloom-7305
title: 'orun5 long-term: checkpoint stall re-measured, one compile then one iteration (ADR-576 holds); REPORT 10.2 closed'
created_at: '2026-10-08T04:21:44+00:00'
parents:
- forest-grove-6707
summary: ''
---
## What

Re-measured the trainer's checkpoint stall (orun5 REPORT §10.2, the last defect carried from orun4 that had not been re-measured), and rewrote §10.2 with the numbers.

## Why

The critic's message named this unit: take the machine lock, run one short foreground training run on an orun5 scratch task, time each checkpoint gap from the trainer's own log, and compare with ADR-576's claim that a checkpoint costs a rollout, not a compile. It is the charter's long-term rung 3 (defects from earlier runs: "the trainer stalls 37–39 s before each checkpoint (measure first)"). Done as asked.

## Method

- Machine idle (GPU 0 %, no `cadex_train` process). Held the machine lock with `flock -n ~/.cache/cadex/training.lock` around the trainer.
- `training/cadex_train.py` run from the `training/requirements.txt` venv, cold (no `--init-from`), on the scratch copy's bundle `orun5-ball-plate/runs/circle-11/train/task_circle_catch-task.json`: `--envs 256 --seed 17 --iterations 60 --checkpoint-every 10`, output to a temp directory (no policy committed).
- The trainer's progress file keeps no per-iteration times, so its stderr was piped through a small stamping filter (`time.perf_counter()` per line, not committed). The gap before each `checkpoint …` line, after the preceding `iteration N` line, is the snapshot + witness + write time.

## Result

- Iteration: 0.431–0.440 s each (after the first two, which carry the `iterate` compile: iteration 0 at 37.0 s from start, iteration 1 +8.8 s).
- First checkpoint (`000010`): **9.54 s** — the one compile of the jitted witness rollout ADR-576 says the first snapshot pays.
- Every later write — `000020` to `000050`, and the four `best` writes, including the one right after the compile: **0.438–0.440 s**, i.e. one iteration. Nine writes in total. The gap at the fifth checkpoint equals the second's; nothing grows with the run.
- Run wall 57.2 s trainer time, 84.7 s total; final witness agrees to 4.0e-08.
- P2's 69–72 s checkpoint spacing (REPORT's earlier text) is 25 iterations of the larger excavator task, not a stall.
- **ADR-576 holds**: a checkpoint costs a rollout after one compile. REPORT §10.2 now says "Measured, and resolved" with these numbers; header verified line moved to `7466b0ed`. Docs-only change; no code, no test touched, so no gates run.
- Per the critic, every criterion and long-term rung now has evidence; the next unit is reconcile and the done claim for review (this iteration did not reconcile — work iterations may not). Tail is now one record.

Dispatch closed: 1 unit — checkpoint stall re-measured: first 9.54 s (one compile), later 0.44 s = one iteration; REPORT §10.2 resolved

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: 7466b0ed32952ab54f237bc48f664066576af9f6

## State Impact

- target: late-pond-2851 — Re-measured 2026-10-08 on a 256-env task: the first checkpoint pays one witness-rollout compile (9.54 s), every later checkpoint and best write costs one iteration (0.44 s); ADR-576 holds and the orun3 stall is gone
