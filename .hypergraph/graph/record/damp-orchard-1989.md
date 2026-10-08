---
node_id: 97773cc0-b7aa-5a4b-8849-02ac136e5187
slug: damp-orchard-1989
title: 'P1 circle-9: unsaturated, doubled off-radius cost moves circle-7''s circling out to 20.6-24.0 mm, 0/8; phase goal next'
created_at: '2026-10-08T03:34:28+00:00'
parents:
- bold-wind-5086
summary: ''
---
## What

Ran P1 circle-9 on `orun5-ball-plate`, the critic's no-code attempt at a pass. It warm-started from circle-7 through ADR-597's curriculum step with a heavier off-radius penalty aimed at the 40 mm circle, and was evaluated on frozen seeds 9101–9108. It fails 0/8, on radius only: the mean radius is 20.6–24.0 mm against a 30–50 bound, up from circle-7's 12–17. Updated REPORT §6, the P1 status row, defects 1 and 11, the done-claim tail, and ledger rows W5 and W7. Commit `bd433547`.

## Why

The critic asked for two things.

1. **Reconcile first** (fold flat-hawk-9763 and bold-wind-5086). **Not done.** This dispatch's rules forbid a work iteration from reconciling ("no exceptions": no hypergraph-reconcile, no `hypergraph update`). The tail is now three records: flat-hawk-9763, bold-wind-5086 and this one. The next reconcile pass must fold all three before the done claim is judged, and REPORT's done-claim paragraph now says so.
2. **Run the no-code attempt.** Warm from circle-7, a heavier off-radius penalty aimed at 40 mm, seeds 9101–9108. **Done as asked.** It failed on radius, so per the critic the phase goal is the next unit. It is not built here, since one unit per iteration.

## Method

- **Diagnosed why circle-7 sat tight.** Its off-radius cost `tanh(|r-40|/10)` is 0.99 at 15 mm and 0.91 at 25 mm, so it is saturated over the radii the policy visits and pays almost nothing for moving out. "Heavier" therefore had two parts:
  - scale 10 → 25 mm, so the cost keeps growing between 12 and 30 mm;
  - weight −0.8 → −1.6;
  - plus alive 1.6 → 2.4, so a step on the plate still pays and early termination is not encouraged.
- **Scoped the change to `task_circle` only**, as a new `circle_radius` list. `task_circle_unsigned` keeps `circle_common`, so its stored policy's digest still matches.
- **Accepted the training script with `--replace`.** The old `policy_circle` declaration was digest-bound to the old task, so the script dropped it for training.
- **Trained** with `cadex_cli.loop.register` + `launch`: `init_from=assets/circle-7.cxpolicy`, `init_from_parent_task=runs/circle-7/train/task_circle-task.json`, 1000 it × 256 envs, seed 15.
- **Stored and evaluated** the result as `circle-9.cxpolicy` (sha bbd88fc9…), redeclared `policy_circle` against it, and ran `cadex evaluate --film none`.

## Result

- The curriculum step was accepted with `the task changed in ['reward']`.
- **circle-8:** the same settings with no `checkpoint_every` and a 570 s budget. It was killed by the budget at iteration 779 and left no policy, so it has no measurement.
- **circle-9:** a 1200 s budget with a checkpoint every 250 iterations. Exit 0, 712 s, witness 8.6e-8. Reward/step peaked at 2.04 (iteration 809) and ended at 1.87.
- **Both ran on the CPU**, because I launched them from a shell with `CUDA_VISIBLE_DEVICES=` (the suites' GPU-hiding habit), and the trainer inherited it. Launch training from a shell with the GPU visible.

Evaluation `46230146b3e0-bbd88fc92f43` passed **0 of 8 seeds**:
- `completed` 1 on 8/8;
- `laps` 3–4 on 8/8 (turns +3.47 to +4.09);
- `mean_distance_mm` **20.6–24.0** (bound 30–50), failing 8/8;
- max distance 32.8–52.8 mm, final distance 15.1–32.1 mm.

So the unsaturated, heavier cost moved the circling mean out by about 7 mm and kept circulation, but **reward reweighting alone does not reach 30–50 mm** in one curriculum step. **The circle task is still not trained to a pass.** P1 stays on the charter's *otherwise* branch, which has its evidence.

Next unit, per the critic's conditional: build the `phase` goal kind (REPORT defect 12) as one unit, with:
- its ADR;
- the pin test across `_GOAL_KINDS`, `GOAL_KINDS`/`goal_values` and the trainer's `draw_goals`/`goals_at`;
- both suites.

Then train a phase-tracking reward warm from circle-9, which is the closest yet.

State of the scratch project: the accepted script declares `policy_circle` → `circle-9.cxpolicy`. circle-7 remains in `assets/`. No policy, trace or checkpoint was committed.

Gates: docs only. `test_licensing_compliance.py` gives 11 passed, 1 skipped. The suites were not rerun because no code changed.

**The tail is three unreconciled records.** The next iteration should be the reconcile the critic asked for.

Dispatch closed: 1 unit — circle-9 (warm from circle-7 by ADR-597, off-radius cost unsaturated and doubled): 3–4 laps on 8/8 at 20.6–24.0 mm vs the 30–50 bound, 0/8 pass; the radius moved by ~7 mm but not to the bound, so the phase goal (defect 12) is the next unit

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: bd433547c83010189d544508fe131c63bc24e98b

## State Impact

- target: peaceful-orchard-2220 — circle-9 (warm from circle-7 via ADR-597, reward only: off-radius tanh scale 10->25 mm, weight -0.8->-1.6, alive 1.6->2.4; commit bd433547): 0/8 pass, laps 3-4 on 8/8, mean radius 20.6-24.0 mm (bound 30-50, circle-7 12-17); reweighting moves radius ~7 mm but not to the bound; next is the phase goal kind (defect 12)
- target: grand-otter-5246 — REPORT §6 circle-9 paragraph and table, status row, defects 1 and 11, done-claim tail (three-record tail); ledger W5/W7 updated with circle-9
