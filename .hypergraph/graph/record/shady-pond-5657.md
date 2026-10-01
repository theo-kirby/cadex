---
node_id: 3d47c602-f0ef-5db9-b8b7-9f58c2733e3c
slug: shady-pond-5657
title: 'ot11 R1 walk round 9 published: r10-steelfoot-fresh valid, 0/10, W10 passes every seed, stands on three feet; r9 a refused start; C1 ledgers 16 runs/22 evals; full cli/tests 1268 passed'
created_at: '2026-10-01T06:04:48+00:00'
parents:
- staid-mountain-7730
summary: ''
---
## What

Published walk round 9 (`r10-steelfoot-fresh`) on `ot11-quad-1`, and moved C1's
two ledgers and REPORT.md with it.

- `docs/probes/ot11/retained/p4-quad-1-r10-evaluation.json`: the round receipt
  (registration, end, checkpoints with their recorded trainer sha, curve,
  mechanism diff, the spec-block check, the evaluation summary, a per-foot table
  and train/eval reward transfer). Filmstrips
  `p4-quad-1-walk-r10-seed-1101-{overview,detail}.png` (170 KB, 145 KB; dark floor).
- README section "Walk round 9".
- `runner/run_ledger.py`: a run whose trainer exited `failed` with no iteration
  run is kept with `attempt: false`; a run whose supervisor has not ended (no
  `wall_time_s`) is listed under `in_progress` and in no total; the receipt
  carries `attempts`. New test `test_a_refused_start_is_no_attempt_and_a_live_run_is_not_counted`
  failed before the change (no `attempt` key) and passes after.
- Regenerated `retained/ot11-runs.json` (16 runs, 15 attempts, r9 `attempt:
  false`, r11 in progress, 23,954.05 s supervised) and
  `retained/ot11-evaluations.json` (22 evaluations, 12 judge scores; only the
  r10 row added). REPORT.md: run rows 15–16, walk total 18,606.07 s, eval row 22,
  revision row r10, failure count "Eighteen of 22", r9 bullet now cites the
  receipt; `test_ot11_report.py` pins moved (16/22/15/18) plus the attempt counts.

## Why

The critic's message: publish r10 after checking HIP_MM and WEIGHT_N against
the evaluation's rig, regenerate both ledgers with r9 as a refused start, move
the pinned counts and prose. The agent had evaluated r10
(`evaluations/2cb0f0e5d80e-34f47b033235`), so the remaining-defects fallback
did not apply. Serves C1 (golden-bay-4173) and R1 (smooth-fountain-9832).
The critic's first item, a full `cli/tests` rerun without `-x` after r11 frees
the GPU, is reported in Result.

## Method

- Validity: evaluated revision 2cb0f0e5 vs registered bd329616 differ only in
  the `assembly.policy` line (script_history 0055 vs 0057). Model 5e28d393 and
  task 2506f000 equal the registration's. Spec block taken from 0057 and compared
  with `retained/walk-spec-block.txt` by Python tokenize (comments dropped): one
  differing token, WEIGHT_N's value. HIP_MM 96.7006 = rig 96.7006 (4 dp);
  WEIGHT_N 5.05069617762 = rig 5.050696177620001 (11 dp). The two permitted
  lines carry trailing comments; recorded as such, not treated as a value
  change. **Valid.**
- Mechanism: r10's MJCF differs from r6's (ade106a6) on 4 lines, the foot
  `<inertial>` mass/diaginertia (1.5345 g -> 10.4746 g); inside session 3's bounds.
- All checkpoints record trainer 97bc1d9a.

## Result

- **r10 fails 0 of 10, valid.** W10 passes on all ten seeds for the first time in
  the walk (−0.029..−0.021 hip heights; r8 −0.095..−0.061). W1, W2 (9.5–14.4°),
  W4 pass. W3 −0.001..0.013, W5 0 steps, W6/W9 undefined, W7 0.59–0.87, W8-low
  0.00 / W8-high 1.00 on all ten. The policy stands still on three feet: RR held
  up (duty 0, ≥ +9.5 mm) on every seed, FL also up on 1103. Reward: alive +3.5,
  speed_error −0.74, diagonal sync −0.40 per step; standing nets +2.14..+2.42
  in evaluation. The agent's r11-speedpay registration reads the same numbers
  and changes only the reward (speed_track 2->4, width 0.4->0.6, speed_error −1->−2),
  warm-started from r10.
- Ledgers: 16 runs, 15 attempts, 23,954.05 s; 22 evaluations; `test_ot11_report.py`
  11 passed.
- **Full `cli/tests`, no `-x`, GPU free (critic's first item):** started
  2026-10-01T05:45:55Z after r11 released the GPU, ended 06:04:33Z: **1268 passed,
  1 skipped, exit 0** in 1,117 s. The skip is `test_review_server.py:851` (needs
  CADEX_REVIEW_HOST). `test_the_same_walk_handles_a_linear_carriage` passed. A GPU
  process sampler every 15 s during the run saw one other venv python process in a
  single sample (06:00:45), gone by the next; no training job overlapped the run.
  `pixi run test-engine` was not run (no engine change in this unit).
- Note: the "trot term removed" in r9/r10's reason refers to the r8 pay term; a
  `trot_sync` cost term is still in r10's reward (−0.40/step). Reported as measured.
- Session 3 has used 2 of its 3 runs (r10, r11). r11 was training when this was
  written; its round is the next publish unit.
- Tail: 2 unreconciled records after this one.

Dispatch closed: 1 unit — r10 published as a valid 0/10 walk evaluation (W10 fixed by steel feet, stands on three feet); r9 marked a refused start; C1 ledgers and REPORT.md regenerated to 16 runs / 22 evaluations

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 78d54930846eb0f8796710e57ba3799c191904b5

## State Impact

- target: smooth-fountain-9832 — round 9 (r10-steelfoot-fresh, steel-ball feet) is a valid evaluation, 0 of 10: W10 passes on all ten seeds for the first time (−0.029..−0.021 HH) but the policy stands still on three feet (W3 ≈ 0, W5 0 steps, RR held up); r11-speedpay (reward-only, warm from r10) trained next
- target: golden-bay-4173 — run_ledger marks refused starts attempt:false and lists live runs in_progress; ot11-runs.json 16 runs/15 attempts/23,954.05 s, ot11-evaluations.json 22 evaluations, REPORT.md pinned to both; full cli/tests 1268 passed, 1 skipped with the GPU free
