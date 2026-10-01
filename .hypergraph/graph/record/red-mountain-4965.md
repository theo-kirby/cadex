---
node_id: 492dedf2-9961-50f6-9647-d8e8fbdd7c5b
slug: red-mountain-4965
title: ot11 R1 walk session 3 diagnosed, pre-registered (mechanism revisable) and launched; P4 warm-start item closed
created_at: '2026-10-01T03:42:38+00:00'
parents:
- happy-cliff-3687
summary: ''
---
## What

Walk session 3 for R1 diagnosed, pre-registered, committed (`fa8e61bc`) before any GPU time, and launched under its supervisor. Also closes the stale P4 item the critic named: the warm-start defect on `wild-harvest-4848` was fixed in iteration 22.

## Why

The critic's message asked for two things in order, and both were done.
1. **The P4 node still lists the warm-start defect as open.** It was fixed in commit `b4c527d0` ("ouroboros #22: no record"). That commit made `loop.run_view` carry `task_bundle` and a `warm_start` line, and made a missing `init_from_parent_task` refused with every run's bundle named. Its test is `cli/tests/test_loop.py::test_a_run_names_its_task_bundle_so_a_warm_start_can_be_registered`, and its ADR is the DECISIONS amendment "a run names its task bundle". `cold-summit-2811` recorded the fix, but declared the impact on `chilly-union-8972` only, so the reconcile never closed the P4 item. Since then the fix has worked in the field: reach-r5, r6-trot and r7-relswing each warm-started through `train_start` with `init_from_parent_task`. This record declares the closing impact on `wild-harvest-4848`. I wrote no separate record for it, because an iteration carries one record.
2. **The unit is walk session 3 (R1, the highest open behaviour criterion).** The order the critic asked for was: diagnosis, then pre-registration, then a commit, then the run under the supervisor. The packaged gate for ADR-467 was deferred to C1, as the critic allowed.

## Method

- **Diagnosis.** Written into `docs/probes/ot11/README.md`, under *Walk session 3: the diagnosis it starts from, and what it may change*. It cites rounds 5–7's receipts:
  - The rear feet drag. RL took 1–6 steps in r5. RL/RR took 2–6/0–7 in r6. On r7's complete seeds they took 6–17/8–13. W9 was ≥2.8 in every round.
  - r7 collapsed. Its reward was −2.11/step at iteration 0, and it stopped at iteration 537. Its `step_*` terms ran −214 to −488 per episode against `alive`'s +1,500.
  - W8-low (0.16–0.29 vs 0.40) and W10 (−0.209 to −0.092 hip heights vs −0.05) did not move under three reward designs.
  - A passive stance already sits at −4.31 mm of W10's −4.84 mm. The agent's own session-2 diagnosis named a mechanism change it was barred from.
- **Session 3 changes one thing.** The product agent may revise the mechanism as well as the task. The bounds:
  - four legs on one free base, with the same four foot bodies in the spec;
  - the floor and global physics (timestep, gravity, solver) unchanged;
  - catalog actuators at catalog limits.
- **The contract follows the mechanism.** The spec block must stay byte-identical to `retained/walk-spec-block.txt`, except `HIP_MM` and `WEIGHT_N`. Those must equal the evaluated model's `rig.hip_height_mm` and `rig.weight_n`, or the evaluation is void. `SPEC_LIFT` keeps its formula.
- **The actor tunes nothing.** The prompt states measurements only and does not say what to change.
- **The pre-registration** is `retained/p4-quad-1-s3-preregistration.json`:
  - Runs: at most 3 (10 in the ledger), each with a budget ≤ 2,400 s and `--stop-on-collapse`. Seeds are the agent's choice, and `train_start` refuses 1101–1110.
  - Turns: at most 2.
  - Driver: `rounds.py` runs with `--max-runs 11`, because the ledger holds 8 evaluations, and `--max-turns 2`.
  - Digests: first prompt `1a5c10c5…`, continuation `019f5160…`, driver `86a96079…`, spec block `487416af…`, and the trainer's digest.
- **Driver change.** `runner/rounds.py` gained `--continue-prompt` (the default is unchanged), so that this session's continuation states its own limits. Session 2's continuation said "four runs in total". Regression test: `test_a_session_may_name_its_own_continuation`, which fails on the old source because argparse rejects the flag.
- **Launch.** `setsid rounds.py … --out ~/cadex-projects/ot11-notes/quad-1-s3` at 03:25:42Z. Its `registration.json` digests equal the pre-registration's. The GPU was idle and no other supervisor was alive.

## Result

- **Walk session 3 is running and unsupervised by any actor.** The product agent's first turn started at 03:25:42Z. No run has been evaluated yet, so R1 is unchanged: 0/10 over seven rounds.
- The next iteration should read `~/cadex-projects/ot11-notes/quad-1-s3/` and the project's `loop-ledger.jsonl`. It should publish each round with the after-check from the pre-registration:
  - the spec block under the mechanism rule;
  - the model digest, hip height and weight;
  - any mechanism change the agent made, and whether it stayed inside the bounds.
- **The P4 warm-start item is closed.** Fix `b4c527d0`, test as above, ADR amendment "a run names its task bundle", already recorded in `cold-summit-2811`.
- **Concerns:**
  - A mechanism change can move hip height and weight. The goal range and shove force in the script are written from `HIP_MM` and `WEIGHT_N`, so if the agent forgets to update them, that evaluation is void, not failed. The prompt says so.
  - `SPEC_LIFT`'s formula assumes the base's geometry (`HX + 20`). If the agent changes `HX` or the legs a lot, the drawn lift may no longer be exactly "the lift that clears a 3° tilt". The after-check should note it, and it is not a contract change.
- **Tests:** `cli/tests` passed 1261, with 1 skipped (18m47s). `pixi run test-engine` was not re-run, because no engine file changed.
- **First sign of the session (read, not yet a result).** The agent re-evaluated r6 (ledger evaluation 9, fail as before, so the driver's evaluation count is now 9, not 8). It then registered `r8-stance` at accepted revision `602c9b45…` with a budget of 2,400 s. Its reason cites r6's W10 (−0.09 to −0.175 hip heights against −0.05), W8-low, W9 and W7, and names a **mechanism change**: a new stance pose (hip 18°, knee −30°), argued from foot sink under load. Because of the extra evaluation, `--max-runs 11` lets the driver start a second turn after two more evaluations rather than three. That only matters if turn 1 ends early, and the prompts' own three-run rule stands.
- The tail is now one record.

Dispatch closed: 1 unit — walk session 3 diagnosed, pre-registered (mechanism revisable, 3 runs × ≤2400 s, stop-on-collapse) and launched under setsid; P4's warm-start item closed against b4c527d0

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: fa8e61bc50b999501fede3477e5f129cb7c9e7fa

## State Impact

- target: smooth-fountain-9832 — walk session 3 pre-registered (commit fa8e61bc, retained/p4-quad-1-s3-preregistration.json) and launched 03:25:42Z under setsid: the diagnosis cites rounds 5-7 (rear feet dragged, W9 >= 2.8 every round; r7 collapsed from -2.11/step; W8-low 0.16-0.29 and W10 -0.209..-0.092 HH unmoved by three reward designs; passive stance at -4.31 of -4.84 mm); the product agent may now revise the mechanism within bounds (four legs, same feet, floor and global physics fixed, catalog actuators; HIP_MM/WEIGHT_N must equal the model's rig); at most 3 runs x 2400 s, stop-on-collapse, 2 turns; first run r8-stance registered with a stance-pose mechanism change; R1 still 0/10
- target: wild-harvest-4848 — the warm-start defect is closed: fixed in commit b4c527d0 (loop.run_view carries task_bundle and a warm_start line; missing init_from_parent_task refused with every bundle named; test_a_run_names_its_task_bundle_so_a_warm_start_can_be_registered; DECISIONS amendment 'a run names its task bundle'), first recorded in cold-summit-2811 against chilly-union-8972 only; used successfully by reach-r5, r6-trot and r7-relswing
