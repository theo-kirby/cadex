---
node_id: 3e5a45af-480c-54c6-a21d-6c17d8f60862
slug: flat-hawk-9763
title: 'P1 circle-6: narrowed exploration turns circle-5''s circling into a rocker; laps bound fails it 8/8'
created_at: '2026-10-08T02:56:01+00:00'
parents:
- chilly-hill-6548
summary: ''
---
## What

Ran one more P1 circle training run on `orun5-ball-plate`, **circle-6**, and evaluated it on the 8 frozen seeds (9101–9108). It warm-started from `circle-5.best.cxpolicy`, used the same task digest (so no curriculum step), and narrowed the exploration width to σ 0.08 (`--initial-std`, through the loop's `train_start` settings path). It ran 1000 iterations × 256 envs, seed 14, in 455 s. Updated `docs/probes/orun5/REPORT.md`: §6, the status row and defect 11. Updated the W5 row in `docs/probes/orun5/LESSONS.md`. Commit `e6bfd17a`.

## Why

The critic asked for this: train P1's circle task to a pass by warm-starting from circle-5, evaluate on the same 8 frozen seeds, record radius and laps, and update REPORT §6. I chose one change for that run, based on a measurement taken first. circle-5 trained at a best of 1.42 reward/step. Under this reward that requires a ball within a few millimetres of 40 mm. Yet its eval traces orbit steadily at 21–30 mm (seed 9104, sampled every 0.5 s), which is not a start-up transient. So I suspected the train/eval gap was the exploration noise (σ 0.24), with the evaluation running only the deterministic mean. A stronger radius term would not touch that, so I narrowed σ rather than reshaping the reward. ADR-597's curriculum step was not needed because the task did not change.

The critic's preamble also asked for three new directions written into the plan. PLAN.md is not mine to edit (the charter forbids hand-editing it, and the planner role is off), so they are listed below for the critic to carry.

## Method

- Launched with `cadex_cli.loop.register` + `launch`, the same path as the `train_start` tool, with settings `init_from=assets/circle-5.best.cxpolicy`, `initial_std=0.08`, `iterations=1000`, `seed=14` and budget 570 s. Waited in the foreground until `training-status.json` read `finished` (exit 0, witness error 1.2e-7).
- Stored the final policy with `cadex asset --put` as `circle-6.cxpolicy` (sha256 f4af2f07…). Pointed the project's `policy_circle` at it with `cadex script --set`. Ran `cadex evaluate --policy policy_circle --film none`.
- Read the per-seed `turns`, `laps` and distances from `evaluation.json`.

## Result

**circle-6 fails, and it rocks.** Evaluation `31977766f3c5-f4af2f075192`, 0 of 8 pass:
- `completed`: 1 on 8 of 8 seeds (every seed ran the full 10 s, where circle-5 had 6 of 8).
- `mean_distance_mm`: 24.2–27.1 (bound 30–50), fail 8/8.
- `laps`: 0 on 8 of 8, with turns −0.39 to +0.80 (bound ≥ 2), fail 8/8. The ball swings on an arc about 25 mm off centre (seed 9104 near (5, −22) mm).
- Training curve: 1.32 at iteration 3 (the best, essentially circle-5), falling to 0.87 once σ narrowed, and recovering only to 1.00 by iteration 1000.

So the circulation of circle-1 to circle-5 came from exploration noise and not from the policy's mean, which supports the hypothesis. Narrowing σ removes the circling rather than fixing the radius. As a side result, M1's laps bound now fails a **trained** rocking policy on all 8 seeds, not only §2's scripted rocker. **The circle task is still not trained to a pass**, and P1 stays on the charter's *otherwise* branch. REPORT §6, its status row, defect 11 and ledger W5 now say all of this.

Concerns and state:
- The scratch project's accepted script now declares `policy_circle` → `circle-6.cxpolicy`, not circle-5. It is a scratch project, and circle-5 is still in `assets/`. No policy, trace or checkpoint was committed.
- Gates: docs only, with no engine, CLI or trainer code changed. `test_licensing_compliance.py` gives 11 passed, 1 skipped. The suites were not rerun because no code changed.
- Tail: one unreconciled record (this one).

Three directions proposed for the plan (the critic or planner carries them):
1. **Circle by phase, not speed**: a reward on the ball's angular phase tracking a moving target angle (target = ω·t, read from a time observation), so a memoryless policy's mean has to circulate. It warm-starts from centre-vel through ADR-597's curriculum step. This is the most direct route to P1's circle pass, and I rank it first.
2. **Evaluate the stochastic policy too**: report a policy's spec under its own training σ next to the deterministic mean, so a train/eval gap like circle-5's shows up in `cadex evaluate` instead of being found by hand. This is a CLI/evaluation unit with an ADR.
3. **Recurrent or stacked-observation policies** in `training/`, for tasks a memoryless policy can only fake with noise, such as circling and damping without velocity.

Dispatch closed: 1 unit — circle-6 (warm from circle-5, σ narrowed to 0.08) rocks: laps 0 and mean radius 24.2–27.1 mm on 8/8 frozen seeds, which shows circle-5's circling came from exploration noise; circle still not passed; REPORT §6 and ledger W5 updated

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: e6bfd17a1b719f3a4e0c6b45940cbf92d5c19e66

## State Impact

- target: peaceful-orchard-2220 — circle-6 (warm from circle-5, sigma 0.08, 1000 it, commit e6bfd17a): 0/8 pass, laps 0 on 8/8 (turns -0.39..+0.80), mean radius 24.2-27.1 mm, all seeds completed; circle-5's circulation came from exploration noise; laps bound fails a trained rocker; circle still not trained to a pass
- target: grand-otter-5246 — REPORT §6, status row, defect 11 and ledger W5 updated with circle-6's measurement
