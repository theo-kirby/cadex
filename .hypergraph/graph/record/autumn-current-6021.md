---
node_id: 7f6e2cf6-8511-5509-ac28-8eacc93d1ba9
slug: autumn-current-6021
title: 'ot11 R1 walk round 12 published: r13-hovercost-margin valid, 0/10, all four feet step but W10 pass is the 3 mm foot margin; rest_height reader; C1 ledgers 19 runs/25 evals; suites green'
created_at: '2026-10-01T08:23:56+00:00'
parents:
- rapid-peak-4236
summary: ''
---
## What

Published ot11 walk round 12, `r13-hovercost-margin` (walk session 4's
second run), as round 11 was published. I added a new probe reader,
`docs/probes/ot11/runner/rest_height.py`, which pays the check round 11's
publication owed: how high each foot rests above the floor, before a W10
pass on a contact margin is read as a fix. Commit `87674b30`.

## Why

The critic's first instruction was to check r13's receipt and, if it had
finished, publish round 12. r13 was at iteration ~400 when I arrived. I
waited for it under the session-4 supervisor (`rounds.py`), never touching
its process, and published once the agent's evaluation was stored.
- **Not done: folding the two unreconciled records.** The critic asked for
  that only if r13 was still running, and it had finished. This dispatch
  also forbids the reconcile skill in a work iteration with no exceptions,
  so I did not reconcile. The tail is now three records
  (`forest-stone-4700`, `rapid-peak-4236` and this one), which meets the
  charter's three-record reconcile trigger. A reconcile pass is due.
- **Done: the cli suite including `test_walk`'s owed tail.** It ran as part
  of the full `cli/tests` run below, while r14 held the GPU.

## Method

- **The receipt.** `training-status.json`: finished, all 800 iterations,
  2,239.22 s supervised and 2,089.69 s in the trainer. Every checkpoint,
  the best policy and the final policy record trainer `97bc1d9a…`, the same
  as `training/cadex_train.py` on disk. The final policy hashes to the
  evaluated `70b9ac55…`.
- **Validity, on the same checks as rounds 9–11.**
  - Registered revision 0067 (`8563f7f5`) against evaluated 0069
    (`0bbe9588`): the diff is only the policy line.
  - Evaluated task `cb33cfe8…` equals the trained task.
  - The model `ab451685…` differs from r12's `5e28d393…` only by
    `margin="0.003"` on the four `c_foot_*/collision0` geoms.
  - HIP_MM = 96.7006 and WEIGHT_N = 5.05069617762 equal the rig.
  - The spec block, comments stripped and tokenized, matches
    `retained/walk-spec-block.txt` (379 tokens) except for WEIGHT_N's value.
- **`rest_height.py`.** It recomputes each foot's height from the stored
  traces with `CadexEvaluation.foot_series`, the feet rebuilt from the
  evaluated model as `w10_reread.py` does. It refuses unless every foot's
  settled lowest height equals the stored one. Over the settled frames it
  reports the p05 and median height, the share at or under `STANCE_MM`
  (1.0 mm), and the share between 1 and 4 mm. I ran it on rounds 10, 11
  and 12, and the agreement check passed on all 30 seeds.
- **Published:**
  - `retained/p4-quad-1-r13-evaluation.json`, in round 11's receipt shape
    plus a `rest_height` block; no machine path;
  - both filmstrips (158 KB and 230 KB, dark floor);
  - both ledgers, regenerated with `run_ledger.py` and `eval_ledger.py`
    over the same projects, in the same order;
  - the REPORT.md tables, the failures and the remaining defects;
  - the README's round 12 section;
  - in `cli/tests/test_ot11_report.py`, the count bumps plus a new test
    pinning the margin finding against the receipt.

## Result

**Round 12 is valid and fails 0 of 10.** Failing on all ten seeds: W3
(0.28–0.64), W6 (0.032–0.038 HH) and W8-low (0.02–0.09). Also failing: W7
on 9 seeds, W9 on 3 and W5-share on 1.

It is the first ot11 walk policy whose every foot steps on every seed
(W5-steps 5–13, passes 10/10). The body is level (tilt 3.6–6.8°, against
23–28° in round 11), heading holds within 9°, and the film shows the legs
alternating with the feet barely off the mat. Training reward was +2.62
per step at the end; evaluation paid +2.13 to +3.09.

**W10 passes on every seed, and the pass is not a fix.** The 3 mm margin
holds every foot's median settled height at +1.5 to +3.5 mm. A loaded foot
in rounds 10–11 rested at −3.1 to +0.4 mm.

**The margin also moves what three other predicates read.** 48–96 % of
settled frames sit between the 1.0 mm stance threshold and 4 mm, bearing
load but read as swing. So W8 and W7 under-read stance and slip, and W5 can
count a hover that moves forward as a step. The verdict is a fail either
way.

**The agent read it the same way.** `r14-margin15-lift` (registered
08:36:27Z, seed 139, 2,400 s, fresh) cuts the margin to 1.5 mm "so a
stance foot is geometrically on the floor", and is training now.

**Ledgers:** 19 runs, 18 attempts, 30,313.69 s GPU; 25 evaluations; r14 in
progress.

**Suites at `87674b30`:**
- `pixi run test-engine`: 2,521 passed, 60 skipped.
- `pixi run python -m pytest cli/tests`: 1,270 passed, 1 skipped, in
  1,234.86 s. This includes `test_walk`, whose tail had been owed since
  round 11; the run shared the machine with r14 on the GPU. I did not
  identify the one skip.
- No engine or payload change, so no packaged gate is owed.

**Concerns for the next iteration:**
- **Publishing r14 must run `rest_height.py` again.** A 1.5 mm margin
  passes that reading only if a loaded foot reads at or under 1.0 mm.
- **The contract has a measured hole.** Nothing in the product refuses a
  contact margin that lifts a foot out of what the frozen predicates read.
  It is listed under Remaining defects. Whether to close it is a recorded
  decision that re-evaluates every earlier policy; it was not taken here.
- **`.ouroboros/goal.md` shows a working-tree modification** that I did
  not make and did not stage. It is the owner's.
- **The unreconciled tail is three records.** A reconcile pass is due.

Dispatch closed: 1 unit — walk round 12 (r13-hovercost-margin) published, valid, 0/10; all four feet step, but its W10 pass and its stance readings are an artefact of the 3 mm foot margin, measured by the new rest_height reader; ledgers 19 runs/25 evals; both suites green

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 87674b30c8d6ec4e30b47e78c2bc3bf17a627ff0

## State Impact

- target: smooth-fountain-9832 — walk round 12 (r13-hovercost-margin, row 25) is valid and fails 0 of 10 on W3, W6 and W8-low; first ot11 policy with every foot stepping on every seed, level body; its W10 pass is the 3 mm foot contact margin holding feet 1.5-3.5 mm above the floor (runner/rest_height.py), which also makes W8/W7/W5 under-read stance; r14-margin15-lift training
- target: golden-bay-4173 — ledgers regenerated (19 runs, 18 attempts, 30,313.69 s; 25 evaluations; r14 in progress), REPORT.md gains the foot-margin remaining defect pinned by a test; test-engine 2521 passed/60 skipped and cli/tests 1270 passed/1 skipped at 87674b30, paying test_walk's owed tail
