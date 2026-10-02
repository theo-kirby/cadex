---
node_id: 26d5a6c5-6a67-5414-8794-28c09874dd3f
slug: round-crane-1720
title: 'ot11 R1: session 6 launched (194d971a); r18-sync-slip published (row 30), valid, passes 2 of 10, slip fixed, W9 remains'
created_at: '2026-10-01T13:32:24+00:00'
parents:
- weathered-river-6058
summary: ''
---
## What

Walk session 6's launch, recorded, and its first round published:
`r18-sync-slip` (run row 24, evaluation row 30) on `ot11-quad-1` is a
valid walk evaluation that passes **2 of 10** seeds (1102 and 1108).
Before this, the best walk round passed 1 of 10.

**Session 6 launch.** The pre-registration is commit `194d971a`,
`docs/probes/ot11/retained/p4-quad-1-s6-preregistration.json` (registered
2026-10-01T12:20:22Z). It covers project head `eb411aad`, accepted revision
`50b2a42c`, model `6cecfa2d`, and task `c1a3ad33`. The scale is
HIP_MM 96.7006 and WEIGHT_N 5.05069617762. The limits are at most 3 runs of
at most 2,400 s each over 2 turns, with `--stop-on-collapse`. The prompts
are `walk.s6.loop.prompt.txt` and `walk.s6.continue.prompt.txt`, and the
driver is `runner/rounds.py` at `86a96079`, unchanged since session 3. It
launched at 12:20 UTC under `setsid`, as rounds.py (pid 2970977) driving
`claude -p --model claude-opus-5-5`. It was confirmed running at the start
of this iteration. Its first ledger row was the agent re-running evaluate
on r17, which hit the same report key `50b2a42caf1c-63cbf22407c0` with the
same verdict. That is not a new evaluation.

**r18-sync-slip**, as registered by the agent at revision `99ab7f0e`:
- a warm start from r17;
- 600 iterations × 2048 envs, seed 181, budget 2,350 s;
- reward weights only: trot_sync 1→2.5, diag_sym 1→2, slip 1.5→2.2,
  speed_error 5→8;
- it finished all 600 iterations in 1,582.47 s of GPU time.

## Why

The critic asked for four things:
1. a causally parented record of session 6's pre-registration and launch.
   This record is it.
2. a fold with the two unreconciled records. **Not done.** This dispatch
   forbids the reconcile skill in a work iteration. The tail is now three
   records (civic-bluff-7621, weathered-river-6058, this one), so a fold is
   due on the next reconcile pass.
3. letting session 6 run under its supervisor and publishing each round as
   it is evaluated, with r17's receipts. Done for r18.
4. replacing the banned bet: the plan's short rank 1, swept clearance from
   an earlier run, is not in the ot11 charter. The bet replacing it is
   about **R1**: publish each session-6 round with its receipts. If a
   round passes all ten seeds, pre-register and commit the confirmation
   evaluation before running it. This moved R1's measured best from 1/10
   to 2/10 and removed W7 slip as a failure mode.

No second GPU job was started.

## Method

- Waited on the project's `loop-ledger.jsonl` until r18 had a
  `train_ended` row and an `evaluated` row.
- Validity checks, the same as r17's:
  - **Revision:** `script_history` 0091 = 0090. 0092 is the registered
    revision: the agent added `sync_w`, `diag_w` and `speed_w`, changed
    `slip_w`, and wired them into the three reward weights. 0093 is the
    policy line `walk_r17`→`walk_r18` with its sha256. 0094 = 0093 is the
    evaluated `f0851df1`.
  - **Model:** evaluated `model_sha256` = trained = `6cecfa2d`. Unchanged
    from r17.
  - **Task:** evaluated = trained = registered `c2303307`.
  - **Policy:** `0ef672db` = the supervisor receipt.
  - **Spec block:** the 30 lines from `HIP_MM =` in 0094 equal
    `retained/walk-spec-block.txt` (sha256 `487416af`) line by line once
    trailing comments are stripped. The one exception is WEIGHT_N
    5.05069617762, which equals `rig.weight_n` 5.050696177620001.
    HIP_MM 96.7006 equals `rig.hip_height_mm`.
  - **Contact offsets:** `contact_offsets` is `[]`, so the round is not
    void (ADR-470).
- Regenerated the ledgers with `runner/run_ledger.py` and
  `runner/eval_ledger.py`. The project order had to match the committed
  receipts; a first pass in a different order reshuffled the evaluation
  ledger and was redone. Totals: 24 runs, 23 attempts, 0 in progress,
  40,325.52 s; 30 evaluations; 12 judge scores.
- Wrote `retained/p6-quad-1-r18-evaluation.json` in r17's receipt schema
  (`ot11-walk-round-receipt-v1`, round 17, session 6), adding the shove
  time and force for each seed. It contains no machine path.
- Committed the seed-1101 filmstrip (187 KB) and detail sheet (219 KB) as
  `p4-quad-1-walk-r18-seed-1101-{overview,detail}.png`, on the dark floor.
- `REPORT.md`: new rows in the run table, the evaluation table and the
  revision table, with GPU totals. Added a "Row 30" reading, a failure
  item, and the R1 remaining-defect paragraph naming session 6 as
  running.
- Moved `cli/tests/test_ot11_report.py`'s pinned counts:
  - 23→24 runs;
  - 29→30 evaluations;
  - 22→23 revisions;
  - 25→26 failed evaluations;
  - 22→23 attempts.

## Result

**r18 is valid and fails 2 of 10.**
- **Passing seeds:** 1102 and 1108 pass all thirteen predicates.
- **W7 slip is fixed:** it passes 10 of 10 at 0.096–0.146 against a limit
  of 0.15. In r17 it failed 8 seeds at 0.154–0.208.
- **W9 still fails on 8 seeds:** the rear feet step 1.56–2.33 times as
  often as the front, against a limit of 1.5.
- **Seed 1107 tips** at 5.90 s, 0.61 s after the largest shove of the ten
  (0.97 N at 5.29 s). It is at 37.6° (W1, W2), and with only 3 steps on
  its least-stepping foot it also fails W5-steps and W5-share.
- **The other nine run the full 10 s:**

  | metric | range |
  |---|---|
  | tilt | 11.7–15.4° |
  | speed_ratio | 0.92–0.97 |
  | clearance | 0.25–0.27 HH |
  | duty | 0.47–0.59 |

- **W10 holds on all ten** (−0.023 to −0.014 HH).
- **Tests:** `test_ot11_report.py` has 13 passed. The full `cli/tests` run,
  CPU-only while r19 trained, has 1271 passed and 1 skipped in 1,116 s.

**Session 6 is live.** The agent's second round, `r19-contact-sync`,
registered at about 13:06 UTC. It warm-starts from r18 for 750 iterations
with a 2,350 s budget, and adds a diagonal-pair contact-state sync cost.
The agent says this is motivated by r18's W9 1.56–2.33 and by diag_sym
showing the joint angles already matched. It is training now under its
own supervisor, and its publication is the next unit. The session has
one more run after r19 (3 maximum). No confirmation evaluation is
registered, because no round has passed all ten seeds.

**Concerns:**
- The reconcile tail is three records, and a fold is due.
- The plan's short bets still name another run's mission-6 clearance
  work. The critic banned them, and this record's bet (R1 session-6
  publication) replaces them only in prose until the next planner or
  reconcile pass.

Dispatch closed: 1 unit — session 6 launch recorded and r18-sync-slip published (row 30): valid, 2 of 10, W7 fixed, W9 remains

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: a279e53ad12db20596beade92e5fbb5a26be364c

## State Impact

- target: smooth-fountain-9832 — walk session 6 (pre-registered 194d971a) is running; its first round r18-sync-slip (evaluation row 30, retained/p6-quad-1-r18-evaluation.json) is valid and passes 2 of 10 (1102, 1108): W7 slip now passes 10/10, W9 rear-heavy stepping fails 8/10, 1107 tips after a 0.97 N shove; best walk round so far, no confirmation registered; r19-contact-sync training
- target: golden-bay-4173 — REPORT.md lists 24 runs (40,325.52 s GPU), 30 evaluations and 23 agent revisions through r18, test-pinned
