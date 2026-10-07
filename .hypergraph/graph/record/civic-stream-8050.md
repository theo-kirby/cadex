---
node_id: 5e61124d-e477-580d-a88f-772ae4593672
slug: civic-stream-8050
title: 'G2 ledger skeleton: 19 reference-project lessons with evidence, destinations undecided'
created_at: '2026-10-06T07:45:16+00:00'
parents:
- light-mist-9160
summary: ''
---
## What

Wrote the skeleton of the G2 ledger, `docs/probes/orun4/LESSONS.md`: 19 lessons from the reference project (the owner's printed STS3215 biped), each phrased as a general rule with its evidence (the project's ADR, revision, run or evaluation, and the change → effect it recorded). Six further choices the charter names are listed as *weighed, no recorded effect*, and two tool defects are routed to F1 and F2. Every Destination cell reads `undecided`.

## Why

The critic's message named this unit: short rung 1, read the reference project end to end (read only), and write the ledger skeleton before deciding where any lesson goes. It serves G2 (`narrow-beacon-6703`), and G1 depends on it, because the base-or-style split is decided per row.

## Method

- Read `DECISIONS.md` (P-ADR-001 to 011) and `PROGRESS.md` in full.
- Read every `runs/walk-r*/` file `run.json` (the training request: filter, `checkpoint_every`, `init_from`, params), `training-status.json` and `stop-requested.json`, whose stop reasons carry the per-run measurements.
- Read all three `evaluations/*/evaluation.json` (r4 i200 fail, r11 i300 fail, r13 i140 pass 10/10).
- Traced `hip_y`, `foot_keel`, `foot_fwd` and `walk_speed` through `script_history/` 0008 to 0032 and the runs' param values.
- Read `script.py`'s thigh, shin, foot, roll-hinge and reward blocks.
- Nothing in the project was written.

Admission rule, from the charter's question policy: a row is a lesson only when the project records a change and what it did. A choice with no recorded effect goes in the *weighed* table. The six areas the charter names are all covered:
- contact geometry: L1 to L4;
- speed against the actuator: L5 and L6;
- lateral clearance: L7 and L8;
- actuator placement: W1;
- training practice: L9 to L18;
- the look: W2 and L4.

## Result

What is true now:
- `docs/probes/orun4/LESSONS.md` exists. It has 19 lesson rows, 6 weighed rows and 2 tool-defect rows, and every destination is `undecided`.
- No code changed, so neither suite was run. The ledger is documentation only, and nothing in Cadex's guidance, tests or defaults names the project.

Findings the next units must know:
- **The charter's speed lesson goes the other way.** The reference moved the target speed **up**, from 100 to 160 mm/s. Every 100 mm/s run found a shuffle or a buzz, and 160 mm/s, still inside the servo's 252°/s, gave real strides. So the rule is "choose a target that full strides reach most easily, then check the actuator's headroom", not "slow down to what the servos hold" (L5).
- **Actuator placement and the look have no measured effect.** The knee servo inside the thigh (W1) and the look (W2) rest only on the owner's approval. They are candidates for the style as taste, not for rules. The next unit should put them in the style and mark them "owner to confirm".
- **F2 evidence.** All 12 runs stopped on purpose carry `training-status.json` `state: stopped`, yet `run.json` `status: failed`. r8, the genuine trainer failure, also reads failed.
- **F1 evidence.** The r11 i300 filtered replay showed heading 15 to 29°. The evaluation, and an unfiltered replay, showed 34 to 63° (L18).

Next: F1, as the critic directed.

Dispatch closed: 1 unit — G2 ledger skeleton: 19 lessons with evidence, 6 weighed choices, destinations undecided.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: c8a4211d53411ce55e8c291d1d5fd01e1665989e

## State Impact

- target: narrow-beacon-6703 — The ledger skeleton docs/probes/orun4/LESSONS.md exists: 19 lessons as general rules with evidence across all six charter areas, 6 choices weighed with no recorded effect, 2 tool defects routed to F1/F2; every destination still undecided, so G2 remains open pending G1's base/style structure and the fresh-session check
