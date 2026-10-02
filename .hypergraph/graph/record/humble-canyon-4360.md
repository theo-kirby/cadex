---
node_id: dbe357f6-9830-5685-8bf2-d34ca576d8f1
slug: humble-canyon-4360
title: 'ot11 R1: r22 published (row 34), valid, 6 of 10; a narrower warm-start width also loses r19''s gait'
created_at: '2026-10-01T17:08:33+00:00'
parents:
- misty-grove-2592
summary: ''
---
## What

Published walk session 7's third round, `r22-gentle-contact25`, on `ot11-quad-1` (commit `6babb356`): run row 29, evaluation row 34. **Valid, 6 of 10** (1101, 1102, 1106, 1107, 1108 and 1109 pass every predicate). The receipt is `docs/probes/ot11/retained/p7-quad-1-r22-evaluation.json`, with no machine paths. Both ledgers were regenerated with the runner scripts: `ot11-runs.json` has 29 runs, 27 attempts, 48,098.03 s and none in progress; `ot11-evaluations.json` has 34 evaluations and 12 judge scores. The seed-1103 filmstrip (170 KB) and detail (245 KB) are committed; seed 1103 is the seed the product filmed. `REPORT.md` is updated in every section: the run table and totals, the warm-start list, the evaluation row and its reading, the revision row, the failure item and remaining defects. The `cli/tests/test_ot11_report.py` counts moved with it. Also corrected: the report had said session 7 would end after r21b. It did not. `runner/rounds.py` reads its run count only between turns, and the agent trained r20, r21b and r22 inside the session's one turn.

Before that, this iteration wrote the record of ADR-471 that iteration 75 never wrote (`misty-grove-2592`), as the critic asked.

## Why

The critic's message asked for three things, in this order:
1. the ADR-471 record, which is done;
2. "if r22-gentle-contact25 is still in flight, publish it first";
3. then a new walk round from r19 with `initial_std` left unset.

r22 was no longer in flight. It had trained and been evaluated, but it was unpublished, and session 7 had closed. Publishing it is therefore the unit before (3), and one iteration holds one unit. It serves **R1** (every earlier run and evaluation is published) and **C1** (the report lists every run, evaluation and revision).

**I did not start the r19 round (3), and I recommend against starting it as the critic phrased it.** r22's own measurement answers the critic's question already:
- r22 warmed r19 at σ 0.12, which is *below* the 0.177 that ADR-471 would carry.
- It still fell from +4.36 per step (iteration 5) to +0.76 by iteration 19.
- At their opening σ of 0.30, r20 and r21b fell the same way.

So a round that differs only by carrying σ 0.177 is predicted to lose r19's gait again. The product agent reached this conclusion on its own when it closed session 7: "No further fine-tune of an evaluated policy until the critic shock is fixed."

On the critic's "frontier stuck / banned bet / choose another criterion" demands, one line each:
- **P1–P4, R2 and R3** have recorded evidence; the owner ticks remain.
- **R1** is the only unmet criterion. Its best result is 9 of 10 (r19), and this round reached 6 of 10. It is not blocked.
- **C1** waits on R1 or on the ceiling (2026-10-03 07:04Z).

There is no other open ot11 criterion to move.

## Method

- **Validity**, the same way as r20 and r21b:
  - `contact_offsets` is empty.
  - The evaluated and trained model hash is `6cecfa2d…`.
  - The task hash `ce70f3dd…` equals the trained task.
  - In script_history 0108, the spec block is byte-identical to 0105's (r21b's evaluated block) and to the frozen `walk-spec-block.txt`, except for HIP_MM and WEIGHT_N, which equal the rig. The source differs from 0105 only in the policy's sha256.
- **Receipt.** The builder (`/tmp`, not committed) first reproduced r21b's published `evaluation` section from r21b's `evaluation.json`, exactly. Then I ran it on r22.
- **Ledgers**:
  - `eval_ledger.py --judges docs/probes/ot11/retained` over w2-negative, robin-negative, robin-1, heron-1 and quad-1;
  - `run_ledger.py` over robin-1, heron-1 and quad-1.
  - The diffs were the r22 row only.
- **Training**: read `runs/r22-gentle-contact25/train/train.log` and `progress.json`, the session 7 log (`ot11-notes/quad-1-s7.log`, one turn) and `runner/rounds.py`'s turn loop.
- **Tests, all CPU-only:**
  - `cli/tests/test_ot11_report.py`: 13 passed.
  - `pixi run test-engine`: 2529 passed, 61 skipped.
  - Full `cli/tests`: 1273 passed, 1 skipped.

## Result

- **r22: 6 of 10, valid.**
  - W7 slip fails 1103 and 1110 (0.195 and 0.156 against 0.15). The worst foot is front-right on all ten seeds; in r21b it was rear-left.
  - W8-low fails 1103 and 1105 (0.399 and 0.355).
  - On 1104, W9 fails at 1.667 and W2 at 30.03° against 30. No seed tips.
  - 1109, r19's only failure, passes W9 at 1.500.
  - Training: 750 iterations, 1,727.12 s of GPU time. The final reading is 3.43 per step; the best is 4.36, at iteration 5.
- **Measured: a warm start loses the source's gait whatever its width.** Three warm starts from r19 all fell to about +1 per step within 20–30 iterations:
  - r20 at σ 0.30 → 0 of 10;
  - r21b at σ 0.30 → 2 of 10;
  - r22 at σ 0.12, learning rate 5e-5 → 6 of 10.

  ADR-471 fixes a real defect, but r22 shows it is not sufficient. The remaining candidate is the fresh critic. Its value estimates are untrained against a converged actor, so the first updates follow noise. This is unmeasured.
- **Handoff, what was tried:** 22 walk attempts over 7 sessions. The reward revisions moved slip, then W9, then W10. r19 reached 9 of 10. Three warm continuations from r19 reached 0, 2 and 6 of 10.
- **Handoff, what to try next (for R1), in order:**
  1. A **trainer unit: critic warm-up on `--init-from`.** For the first N iterations, update only the value function, with the actor frozen and no policy step. It needs a flag, a regression test that measures the actor unchanged through the warm-up, and an end-to-end test in the training venv. It changes no `.cxpolicy` format and nothing in the engine, so it is smaller than carrying the critic, which would need a container change. It is pipeline work that the actor may do, and it touches no reward or spec.
  2. Then pre-register and launch session 8 from r19 with `initial_std` unset (carried σ) and the warm-up on. The agent chooses its task.
  3. Alternatively, the agent may evaluate r22's `walk_task.best.cxpolicy` (iteration 5, the policy closest to r19). The agent decides this; the actor does not.
- **Concerns:**
  - `ot11-notes/quad-1-s7/rounds.json` `standing` reports `runs_this_session: 23`, because `summarise()` calls `standing(project)` without `ended_before`. This is a reporting defect in the session summary only; the stop rule passes `ended_before`. It is unfixed.
  - The reconcile is overdue. The tail is now four records: forest-rose-3078, southern-rain-8433, misty-grove-2592 and this one. This work iteration may not fold them.
- No new dependency. No GPU job was started. Two record nodes were written this iteration: the critic-ordered ADR-471 record and this unit's record.

Dispatch closed: 1 unit — published r22 (row 34, valid, 6 of 10) and measured that a narrower warm-start width also loses r19's gait, so ADR-471's carried σ is not sufficient

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 6babb356de9a5be78ecf0bc63d6e40ce2a7789a5

## State Impact

- target: smooth-fountain-9832 — r22-gentle-contact25 (run row 29, evaluation row 34) published: valid, 6 of 10 (1101, 1102, 1106-1109); fails W7 on 1103/1110, W8-low on 1103/1105, W9 and W2 (30.03 deg) on 1104; warm from r19 at sigma 0.12 it still fell +4.36 -> +0.76 by iteration 19, so three warm starts (sigma 0.30, 0.30, 0.12) all lost r19's gait and ADR-471's carried width is not sufficient; next candidate is a critic warm-up on --init-from; commit 6babb356
- target: golden-bay-4173 — REPORT.md carries run row 29 (29 runs, 27 attempts, 48,098.03 s GPU) and evaluation row 34 (34 evaluations), revision row and failure item for r22, and corrects the session-7 driver note (all three runs trained in one turn); test-engine 2529 passed 61 skipped; cli/tests CPU 1273 passed, 1 skipped
