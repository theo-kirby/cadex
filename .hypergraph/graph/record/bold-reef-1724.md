---
node_id: 1806ff5e-b13a-5d33-a93c-bb03b97f89c9
slug: bold-reef-1724
title: 'ot10: W2 run 1 on ot10-quadruped-3 — pre-registered, 1000x2048 trained, walked=false, diagnosed'
created_at: '2026-09-28T15:21:53+00:00'
parents:
- golden-falcon-9792
summary: ''
---
## What
W2 run 1. I committed the settings and stop rule to `docs/probes/ot10/README.md` (commit `d94c845f`) before any GPU use. Then I ran one bounded `cadex walk` on a copy of the best-scoring passing A5 design, and published the gait verdict, the training curve and a diagnosis (commit on top of `d94c845f`). **`walked = false`.**

## Why
The critic's message named W2 as the next unit: choose the best-scoring passing A5 design, commit seed, budget, wall-clock cap, the unchanged ADR-410 overlay and `--stop-on-collapse` before the run, then launch one bounded walk on a copy, so the A5 project stays read-only. I did that. The biped and the quadruped tie at 15/21, and the hexapod scores 14. The tie went to `ot10-quadruped-3`, because W2's bar is `walked = true` and a quadruped stands without balancing. The critic also asked for the hexapod's triangle count and a video size. The chosen design is the quadruped, so I measured the quadruped's instead: 78,419 drawn triangles, decimated from 650,316 at a 0.59 mm cell. I did not render its W1 video in this unit; that is the next unit.

## Method
- Pre-registration table in the README, committed before launch. Design `ot10-quadruped-3` @ `7de6eea6212e`, copied with `cp -a` to `~/cadex-projects/ot10-quadruped-3-w2`. Command `./cadex walk --project <copy> --out <copy>/runs/w2-1 --iterations 1000 --envs 2048 --seed 0 --timeout 10800 --json`. No `--prompt`, so no tokens and no geometry change. Local RTX 5090, `~/cadex-train-venv`. `--stop-on-collapse` is passed by the walk, and I confirmed it in the trainer's argv. Grounding enforced, thresholds unchanged.
- Launched with `setsid nohup` at 14:23:23Z, stdout and stderr in `~/cadex-projects/ot10-notes/w2-1/`, outside git.
- I read `review.json` from the walk's JSON envelope and `train/progress.json` for the curve.

## Result
- **What is true now.**
  - The walk exited 0 after 2,241.7 s: train 1,944.8 s, declare 59.5 s, roll-out 130.9 s, then review.
  - The trainer ran all 1,000 iterations on the GPU in 1,611 s and never collapsed. Reward per step rose from 1.16 in the 0–99 bucket to 2.62 in 900–999, with the best at the last iteration (2.654), still rising.
  - The policy is stored (`d8b87d2e1215…`, witness agrees to 1.2e-7) and declared through the walk's own path, at revision `f6d32a586ecc…`, digest `7d7f0c2eca9e…`.
- **Gait: did not walk.**
  - Tipped past 45° at 4.36 s, and the `tipped` termination fired at step 218 of 500.
  - 97.7 mm of planar travel: +19 mm forward, −96 mm sideways, heading −52°.
  - Training survival read 0.43.
  - Roll-out reward totals: alive 438, upright 207, speed error −203, sideways −45, yaw −39.
- **Diagnosis.**
  - (1) It learned to stand. The roll-out speed error averages 0.93 per step, about 7% of the 80 mm/s target. Under the ADR-410 weights, standing nets about +2 per step and walking adds at most +1.
  - (2) The tip falls inside the task's 2–8 s disturbance window, and the review does not record push times.
  - (3) A defect in the gait check: `training_survival` reads only the last iteration's episode length. That was 213.3, while the last-50 median is 487.6, and the trainer's episode figure exceeds the 500-step horizon (1,647 mean in bucket 0), so it is not a clean fraction. (1) and (2) carry the verdict without it. Not fixed.
- **W1.** The quadruped draws 78,419 triangles, below Finch's 95,212, so W1's 512 px, 300 s bound applies with no extra decimation.
- **Next.** First render the W1 video of `w2-1`'s policy on this model. Then pre-register a second bounded run, warm-started with `--init-from` on the unchanged task digest, with the same thresholds. A reward change would need a new design turn, not an actor edit.
- **Concerns.**
  - The walk committed into the copy's own project git (`2b3e638`); the original `ot10-quadruped-3` is untouched.
  - My first wait loop's `pgrep -f` matched its own command line. The walk had ended at about 15:00Z, before I noticed.
- The tail is 3 unreconciled records, so a reconcile is due.

Dispatch closed: 1 unit — W2 run 1 pre-registered, trained and reviewed on a copy of ot10-quadruped-3: walked=false (stood, tipped at 4.36 s), diagnosed

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 4074b33c48c8d65fba4c0859831bed7e34b49b0f

## State Impact

- target: golden-garden-8501 — W2 run w2-1 measured end to end on a copy of ot10-quadruped-3 (pre-registered d94c845f; 1000 it x 2048 envs, seed 0, no collapse, policy d8b87d2e stored/declared/verified): walked=false — tipped at 4.36 s with 19 mm forward travel; policy learned to stand; next is a pre-registered warm-start run
- target: late-pond-2851 — gait check's training_survival reads a single last-iteration episode length (213 vs last-50 median 488) and the trainer's episode figure exceeds the horizon; recorded defect, not fixed
