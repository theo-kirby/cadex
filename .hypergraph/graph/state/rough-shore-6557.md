---
node_id: 9caf8458-637b-5a76-910b-ab872b7f9681
slug: rough-shore-6557
title: P1. Each behaviour has a frozen evaluation contract, and it catches the known failures
created_at: '2026-09-30T07:04:57+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot11: **P1. Each behaviour has a frozen evaluation contract, and it catches the known failures.** The charter asks `docs/probes/ot11/README.md` to freeze, for walk, reach and balance and before any ot11 training run: a success spec (predicates on a rollout trace, independent of the reward); ten or more evaluation seeds with reset variation and disturbances; a pass rule; a blind video judge (frozen rubric, one-paragraph intent, filmstrip frames on the dark prototype floor, nothing else) and its pass bar. Known negatives are measured before anything new is trained: ot10's `w2-2` shuffle must fail the walk spec for the right reason, and ot9's Robin is measured against the balance spec. Changing a frozen item later is a recorded decision that re-evaluates every earlier policy. The human owns the charter checkbox; roles report results and do not tick it. Declared target: `gap-p1-each-behaviour-has-frozen` [rec: kind-spire-3578].

**Done so far** [rec: proud-lantern-5203] [rec: ready-field-7940]:

- **The contract is frozen.** `docs/probes/ot11/README.md` and `contract.json` freeze walk (W1–W10), reach (Q1–Q4) and balance (B1–B5) predicates, none reading the reward; seeds 1101–1110 with reset variation, goals and shoves; the pass rule (every seed, every predicate); and the blind judge's rubric (SHA-256 pinned), inputs, judged seeds 1101/1105/1110 and bar (9 of 12, no trait below 2). Committed at `ff066f1b` before either negative was read. One change since: W10 (no foot below −0.05 hip heights), ADR-454 at `34ac3ab2`, made before any training, with both negatives re-measured under it. `cli/tests/test_ot11_contract.py` holds the README and the JSON equal [rec: proud-lantern-5203].
- **`w2-2` fails the walk spec for the right reason.** Stored rollout: fails W3 (1.91× the commanded speed), W5 (steps carry 14–38 % of each foot's travel), W7 (stance slip 0.32–0.67 of path), W9 (front feet step 4.2× the rear) and W10 (feet up to 21.3 mm below the floor); passes W1, W2, W4, W6, W8, which is all the old gait check read. On the ten contract seeds it fails all ten, with W5, W7, W9, W10 failing on every seed. Receipts: `docs/probes/ot11/retained/p1-w2-2.json`, `p1-w2-2-seeds.json`. The commanded speed is taken as 80 mm/s, from its task's reward [rec: proud-lantern-5203].
- **Robin fails the balance spec: it wanders and turns.** B3 fails on all ten ot9 seeds (829–851 mm drift, limit 104.8 mm) and B4 on all ten (131° heading, limit 20°); B2 passes on all ten. B1 and B5 are not measured, because its traces ran 8.0 s with no shove. Receipt: `retained/p1-robin.json` [rec: proud-lantern-5203].
- **The predicates are read through the product's metrics.** `docs/probes/ot11/runner/measure.py` is only the contract's binding onto `CadexEvaluation`, and reproduces both receipts to 1.3e-15. Q1–Q4 now have a reader, pinned on synthetic reaches only [rec: ready-field-7940].

Both negative readings are off-contract (the policies' own task conditions), so they can fail and cannot pass; the contract's conditions need the evaluation command (P2) and goal sampling (P3) [rec: proud-lantern-5203].

**Missing, so it stays open** [rec: proud-lantern-5203]:

- The blind video judge has not run on either negative. No filmstrip renderer or judge runner exists yet [rec: proud-lantern-5203] [rec: ready-field-7940].
- The cause of `w2-2`'s feet going 21.3 mm below the floor is unmeasured. The heights equal MuJoCo's geom positions, so it is in the rollout; soft contact, 1.5 g feet and strong servos are a guess. A walk policy can exploit it, so it needs measuring before R1 trains [rec: proud-lantern-5203].
- The reach spec has no known negative [rec: proud-lantern-5203].

## Negative knowledge

None yet.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
- proud-lantern-5203 — contract frozen (ADR-454); w2-2 and Robin measured failing; judge not run, floor penetration unexplained
- ready-field-7940 — contract predicates read through the product's metrics; Q1–Q4 gain a reader
