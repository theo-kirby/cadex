---
node_id: 80864c7e-4624-51cd-9874-c9064ef05610
slug: misty-water-8806
title: 'P2 finished: cold run with S2 load + R1 track-frame goal halves the reach floor (11.5 mm, 7/10 vs 23.6 mm, 2/10)'
created_at: '2026-10-08T00:52:09+00:00'
parents:
- hidden-sand-7542
summary: ''
---
## What

This unit finishes P2. The cold run `reach-p2-cold` has its evaluation numbers, the open record `hidden-sand-7542` is filled in, and the ledger's W8 and W9 rows are closed. No Cadex code changed.

## Why

The critic's message named this as the first fix and the next unit: replace RESULT PENDING in `hidden-sand-7542` with the evaluation of `reach-p2-cold` on the frozen seeds 101–110, unless an existing evaluation already held it (check the digest). One did, so nothing was re-run. The long-term rung the critic named next, the base guidance for sensors, linkages and motion predicates, is left for the next iteration, because the budget is one unit.

## Method

- `runs/reach-p2-cold/training-status.json`:
  - exit 0, 1400 iterations, best reward per step 4.75 at iteration 1397;
  - final policy `0d2cb91d…`.
- `sha256sum` matches `runs/reach-p2-cold/train/reach.best.cxpolicy` with the project's declared `assets/reachp2_best.cxpolicy`, `5dc8fc5a…`. The previous session declared it (`edit_script`, project commit `35bd7f6`) and evaluated it after writing its record, then errored before updating the record.
- The evaluation `evaluations/0c0b7e5b05e5-5dc8fc5abd8a/evaluation.json`:
  - `policy_sha256` is `5dc8fc5a…`;
  - `task_sha256` and `trained_task_sha256` are both `ea19ce4a…`, the cold run's task, with S2 load observations and the R1 track-frame goal;
  - seeds 101–110 under reach-05's unchanged spec.
- Per-seed `final_error_mm_max` was read from its `seeds[].metrics`. reach-05's came from the same project's `evaluations/1c1fb7479500-0c40b34750ac`, the reference copy.
- The final iteration-1400 policy `0d2cb91d…` was not evaluated separately. Declaring the best checkpoint is the reference's own practice (`reach05_best`).

## Result

**The ~20 mm floor moved.** On the same frozen seeds and spec:

| Policy | Final error per seed 101–110 (mm) | Median | Pass (≤ 15 mm) |
|---|---|---|---|
| reach-p2-cold (best) | 3.4, 17.2, 21.4, 2.5, 10.6, 5.2, 22.4, 12.5, 6.0, 12.4 | 11.5 | 7/10 |
| reach-05 (reference) | 11.0, 32.6, 25.1, 25.4, 26.7, 13.7, 20.8, 22.1, 39.3, 18.7 | 23.6 | 2/10 |

- 9 of 10 seeds improved; only seed 107 got worse (20.8 to 22.4 mm). Seeds 102, 103 and 107 still fail, so the spec still fails overall.
- Max tilt was 0.06° and max drift 8.6 mm.

Together with `hidden-sand-7542`'s probes:
- servo sag is ruled out directly: load ≤ 0.19 of stall, tip shift ≤ 4.3 mm;
- the reference floor was already in the policy's commands.

**Concern: the move is not attributed.** One run changed three things at once:
- the goal frame;
- the load channels;
- an uninterrupted 1400-iteration schedule, where the reference ran a 600 + 400 + 400 warm chain.

There is also a measurement caveat. The new error is measured against the goal where it sat in the track frame each frame (R1), and the reference's against a goal fixed in the world. The bases drift at most 8.6 mm. The earlier probe's agreement check showed the reference errors reproduce in the track frame. To separate the causes, the next run would be the same schedule with a world-fixed goal. It was not done here.

Ledger: W8 and W9 in `docs/probes/orun5/LESSONS.md` now read *replaced*, with these numbers. W3 and W12 still say *open* even though L1 landed (ADR-593..595); C1 should update them. The unreconciled tail is now two records.

Gates: only docs and records changed, so the suites were not rerun.

Dispatch closed: 1 unit — P2 finished: reach-p2-cold median 11.5 mm, 7/10, vs reach-05 23.6 mm, 2/10; the floor moved, cause not separated

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: 3c669ced5caf223342b0d05850697e6ea7c73c76

## State Impact

- target: true-moon-7226 — reach-p2-cold evaluated on seeds 101-110 (evaluations/0c0b7e5b05e5-5dc8fc5abd8a): median final error 11.5 mm, 7/10 pass vs reach-05 23.6 mm, 2/10; 9/10 seeds improved; sag ruled out by direct probe; the move is not attributed between goal frame, load channels and the uninterrupted 1400-iteration schedule
