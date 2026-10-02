---
node_id: b7165a26-d835-5028-b7e5-c01fc3cd1543
slug: proud-lantern-5203
title: 'ot11 P1: the evaluation contract is frozen, and w2-2 and Robin both fail it for the stated reasons (ADR-454)'
created_at: '2026-09-30T07:37:39+00:00'
parents:
- kind-spire-3578
summary: ''
---
## What

The record iteration 2 owed and did not write. P1's evaluation contract for ot11 is frozen, and both known negatives are measured against it (commits `ff066f1b` and `34ac3ab2`).

- `docs/probes/ot11/README.md` and `contract.json` freeze, for walk, reach and balance: a success spec as predicates on the rollout trace (W1–W10, Q1–Q4, B1–B5), none reading the reward; ten evaluation seeds 1101–1110 with reset variation, goals and shoves; the pass rule (every seed, every predicate); a blind video judge with its rubric (SHA-256 pinned), inputs, judged seeds 1101/1105/1110 and bar (9 of 12, no trait below 2).
- `docs/probes/ot11/runner/measure.py` reads the walk and balance predicates from a trace. `cli/tests/test_ot11_contract.py` holds the README and the JSON equal; `cli/tests/test_ot11_measure.py` pins each predicate on a synthetic trace that passes it and one that fails it.
- ADR-454 records the contract and the one change made after the freeze: W10 (no foot below −0.05 hip heights).

## Why

P1 is the charter's first criterion and the top of the horizon ladder: the evaluation must be trustworthy before anything is trained. The critic's message for this iteration asked for this record first, because iteration 2 committed the work with no record and no test evidence ("ouroboros #2: no record").

## Method

- The contract was committed first (`ff066f1b`), with nine walk predicates, before either negative was read.
- `w2-2` (ot10-quadruped-3-w2, policy `7a4e8c23…`, model `49d11013…`) was then read from the project's stored rollout, and rolled again on the ten contract seeds by `CadexDynamics.rollout_policy` from the run's stored bundle, under its own task's conditions.
- Robin (ot9-robin, policy `ef71f370…`) was read from the ten stored ot9 evaluation traces (ot9 seeds 0–9, 8.0 s, no shove).
- Both projects are read-only and nothing was written to either. Both readings are off-contract: they can fail and cannot pass.
- Test evidence, run this iteration from the start of the session at `34ac3ab2` (`pixi run python -m pytest cli/tests -q`; working-tree edits for the next unit began while it ran, so the final-revision run is in that unit's record):

```
...........................s............................................ [ 77%]
.......................................                                  [100%]
1118 passed, 1 skipped in 879.72s (0:14:39)
```

## Result

What is true now:

- **The contract is frozen** for walk, reach and balance, with seeds, conditions, pass rule, rubric and bar. One recorded change since the freeze: W10 (ADR-454), made before any training; both negatives were re-measured under it.
- **`w2-2` fails the walk spec for the right reason.** Stored rollout: fails W3 (1.91× the commanded speed), W5 (steps carry 14–38 % of each foot's travel; 18, 21, 5, 7 steps of 60, 66, 48, 61 swings), W7 (stance slip 0.32–0.67 of path), W9 (front feet step 4.2× the rear) and W10 (feet up to 21.3 mm below the floor). Passes W1, W2, W4, W6, W8, which is all the old gait check read. On the ten contract seeds it fails all ten; W5, W7, W9, W10 fail on every seed. Receipts: `docs/probes/ot11/retained/p1-w2-2.json`, `p1-w2-2-seeds.json`.
- **Robin fails the balance spec: it wanders and turns.** B3 fails on all ten seeds (829–851 mm drift, limit 104.8 mm) and B4 on all ten (131° heading, limit 20°). B2 passes on all ten. B1 and B5 are not measured: its traces ran 8.0 s with no shove. Receipt: `retained/p1-robin.json`.

What P1 still lacks, so it stays open:

- **The video judge has not run on either negative.** The filmstrip renderer and the judge runner do not exist yet; the rubric and bar are frozen ahead of them.
- **The cause of the floor penetration is unmeasured.** `w2-2`'s 7.5 mm feet go 21.3 mm under the plane. The reader's heights equal MuJoCo's geom positions, so it is in the rollout; soft contact, 1.5 g feet and strong servos are the guess, not a measurement. A walk policy can exploit it, so it needs measuring before R1 trains.
- The reach spec has no known negative, and at the time of this unit had no reader.
- Both negative readings ran under the policies' own task conditions. The contract's conditions (its shoves, its commanded speed range, 10.0 s for Robin) need the evaluation command (P2) and goal sampling (P3).

Assumption carried: the commanded speed for `w2-2` is taken as 80 mm/s, which is what its task's reward asked for.

Dispatch closed: 1 unit — P1 contract frozen and both known negatives measured failing for the stated reasons; judge not yet run.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 34ac3ab26ad29b0c4477d9fda230ecb9b7aa553e

## State Impact

- target: rough-shore-6557 — still open. Contract frozen for walk, reach and balance (commit ff066f1b; W10 added by ADR-454 in 34ac3ab2 before any training). Known negatives measured off-contract: w2-2 fails W3, W5, W7, W9, W10 on its stored rollout and fails all ten contract seeds; Robin fails B3 and B4 on all ten ot9 seeds, B1 and B5 not measured. Missing: the blind video judge has not run on either negative (no filmstrip renderer or judge runner yet), and the cause of w2-2's feet going 21.3 mm below the floor is unmeasured.
