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

**Done so far**:

- **The contract is frozen.** `docs/probes/ot11/README.md` and `contract.json` freeze walk (W1–W10), reach (Q1–Q4) and balance (B1–B5) predicates, none reading the reward; seeds 1101–1110 with reset variation, goals and shoves; the pass rule (every seed, every predicate); and the blind judge's rubric (SHA-256 pinned), inputs, judged seeds 1101/1105/1110 and bar (9 of 12, no trait below 2). Committed at `ff066f1b` before either negative was read. One change since: W10 (no foot below −0.05 hip heights), ADR-454 at `34ac3ab2`, made before any training, with both negatives re-measured under it. `cli/tests/test_ot11_contract.py` holds the README and the JSON equal. The contract text has not changed since; only the README's measured section has been rewritten [rec: proud-lantern-5203] [rec: glad-fjord-0764].
- **The predicates are read through the product's metrics.** `docs/probes/ot11/runner/measure.py` is only the contract's binding onto `CadexEvaluation`, and reproduces the off-contract receipts to 1.3e-15. Q1–Q4 have a reader, pinned on synthetic reaches only [rec: ready-field-7940].
- **Both negatives are measured through the product on the contract's seeds, shoves and horizon**, with `cadex evaluate`, on two copies (`ot11-w2-negative`, `ot11-robin-negative`) whose specs declare `randomisation=[]` because the contract lists none. Receipts: `docs/probes/ot11/retained/p2-w2-2-evaluation.json` and `p2-robin-evaluation.json`, pinned by `cli/tests/test_ot11_contract.py`. No seed was void on either [rec: misty-timber-4175] [rec: glad-fjord-0764].
- **`w2-2` fails the walk spec for the right reason: 0 of 10 seeds pass.** W5 (fewest steps 0 to 3 against ≥ 4; step share 0.00 to 0.08 against ≥ 0.70) and W7 (slip 0.49 to 0.81 against ≤ 0.15) fail on all ten, as do W9 and W10. W2 fails on eight, `tipped` fires on 1107 and 1110, and W6 passes on six. The slowest seed moves at 47 mm/s. The seed the reward paid most is 1109 (836.0), whose least-stepping foot took one step. The walk spec on that copy is W1, W2, W4's heading and W5–W10: W3 and W4's lateral half need a goal (P3) [rec: glad-fjord-0764] [rec: misty-timber-4175].
- **Robin fails the balance spec: 0 of 10 seeds pass.** B3 (9.2 to 18.7 COM heights of drift), B4 (131° to 168°) and B5 fail on all ten, and `fallen` fires on six, between 3.10 s and 9.08 s. Only two seeds recover from both shoves. B1 and B5 are measured here for the first time; ot9 never shoved it. Its task never randomised, so the numbers are the same with and without `randomisation=[]` [rec: misty-timber-4175] [rec: glad-fjord-0764].
- **Both negatives are filmed on the judged seeds 1101, 1105 and 1110**, from the kept traces with no new rollout: `w2-2` on the contract's walk window (5.0 s, 0.04 s), Robin from each seed's first shove onset at 0.2 s (seed 1110's window slid back to end at its 4.26 s fall). The receipts gained a `film` block and nothing else; seed 1101's four sheets are committed under `docs/probes/ot11/` (107 KB to 258 KB) [rec: mild-horizon-5182].

Earlier readings, kept for the record: the stored-rollout and own-conditions receipts (`retained/p1-w2-2.json`, `p1-w2-2-seeds.json`, `p1-robin.json`) were off-contract, where `w2-2` also failed W3 at 1.91× a commanded speed taken as 80 mm/s from its reward [rec: proud-lantern-5203]. ADR-457's first on-contract reading of `w2-2` kept the task's mass randomisation and is superseded: those were different episodes, since the mass draw came first in each seed's stream [rec: glad-fjord-0764].

**Missing, so it stays open**:

- The blind video judge has not run on either negative. The filmstrips it needs exist; its runner does not [rec: mild-horizon-5182].
- The product's detail view follows the design's centre rather than a named base, and side-on is derived from the path. Whether that needs a recorded contract decision is unruled [rec: mild-horizon-5182].
- W3, W4's lateral half and Q1–Q4 cannot be stated in a product spec until a task can state a goal (P3) [rec: misty-timber-4175].
- The cause of `w2-2`'s feet going 21.3 mm below the floor is unmeasured. The heights equal MuJoCo's geom positions, so it is in the rollout; soft contact, 1.5 g feet and strong servos are a guess. A walk policy can exploit it, so it needs measuring before R1 trains [rec: proud-lantern-5203].
- The reach spec has no known negative [rec: proud-lantern-5203].
- The reset lift in each copy's spec is the task's own clearing lift plus the contract's 0–5 mm; no smaller clearing lift was searched for [rec: misty-timber-4175].

## Negative knowledge

- [scope: `w2-2` on the contract seeds with its task's 0.85–1.15 tray-mass randomisation kept (ADR-457's reading) | confidence: high | evidence: misty-timber-4175, glad-fjord-0764] That reading is not the contract's conditions and must not be cited or filmed: it showed W6 failing on all ten, three seeds sitting back at about 43° under 5 mm/s and seed 1104 as best paid, none of which holds on the mechanism as built. The superseded report is `evaluations/60f655537c0b-*` in `ot11-w2-negative`.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
- proud-lantern-5203 — contract frozen (ADR-454); w2-2 and Robin measured failing; judge not run, floor penetration unexplained
- ready-field-7940 — contract predicates read through the product's metrics; Q1–Q4 gain a reader
- misty-timber-4175 — both negatives measured through cadex evaluate on the contract's seeds, shoves and horizon (ADR-457); B1 and B5 measured
- glad-fjord-0764 — both negatives re-measured with randomisation=[] (ADR-458); the drawn-mass reading superseded
- mild-horizon-5182 — both negatives filmed on the judged seeds (ADR-459); judge still not run
