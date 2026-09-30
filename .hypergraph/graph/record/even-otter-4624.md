---
node_id: 91814061-95b6-5fc9-b520-cb6b07b0665e
slug: even-otter-4624
title: 'ot11 R3 confirmation: policy 8919a22d passes the frozen balance spec on 10 of 10 seeds and meets the blind judge''s bar on all three judged seeds; spec and judge agree'
created_at: '2026-09-30T18:43:50+00:00'
parents:
- soft-otter-1938
summary: ''
---
## What

R3's confirmation evaluation, which the critic asked for as one unit.
It had three steps: pre-register, commit, then run `cadex evaluate` and the
frozen blind judge.

- **Pre-registration**, committed before anything ran (`c2dd99bb`):
  `docs/probes/ot11/retained/r3-confirm-1-registration.json`. It fixes:
  - the policy `8919a22d…` (bal-1's iteration-400 checkpoint);
  - the accepted revision and the task and model digests;
  - the spec's canonical-JSON digest `64a41714…`;
  - the ten frozen seeds, the conditions, B1–B5 and the pass rule;
  - the void rule;
  - the judge runner's digest, judged seeds 1101/1105/1110, three calls a
    seed and the bar;
  - the exact commands, and that it is run once.
- **Evaluation**: `./cadex evaluate --project ot11-robin-1 --out
  evaluations/r3-confirm-1 --film 1101,1105,1110`. Receipt:
  `retained/r3-confirm-1-evaluation.json` (engine paths stripped).
- **Judge**: `runner/judge.py balance` on each judged seed. Receipts:
  `retained/judge-r3-confirm-1-seed-{1101,1105,1110}.json`.
- A README section, "R3's confirmation evaluation", with both tables.

## Why

This is the critic's named next unit, as one unit. It serves
`staid-tooth-3475` (R3). The last iteration settled evaluation trust for
this policy: MJX/MuJoCo observation parity, and the ledger link. So the
confirmation was the remaining step. I did what the critic asked, with no
deviation.

## Method

1. Checked the project still declares `8919a22d` (script.py line 512). The
   run's MJCF hashes to the model digest the evaluation reads (`89ce4ad7`).
   The project's `bundle/robin_model-model.xml` is still ot9's `933b1ac6`
   and is not what evaluate reads.
2. Wrote the registration from `contract.json` and the round evaluation's
   identity, then committed it alone.
3. Ran evaluate once: 3 min 44 s, most of it the seed-1101 video. Checked
   these conditions:
   - verdict `pass`;
   - `summary.void` empty;
   - no solver warnings;
   - the spec digest equal to the registered one;
   - every shove force inside [0.10, 0.25] × weight.
4. Ran the three judged seeds' judges in parallel, three calls each, with
   the frozen isolation.

## Result

**True now.**

- **The spec: pass, 10 of 10 seeds, none void.** Worst seed on each
  predicate:

  | predicate | worst seed | limit |
  |---|---|---|
  | B2 tilt | 11.5° (1110) | 30° |
  | B3 drift | 0.92 COM heights, 48 mm (1108) | 2.0 |
  | B4 heading | 0.97° (1102) | 20° |
  | B5 recovery | 0.42 s (1102) | 2.0 s |

  B1: all ten seeds ran 10.0 s and ended by truncation.
- **Every seed's metrics equal bal-1's round evaluation exactly.** The
  rollout is deterministic per seed. This confirmation therefore
  reproduces that round's measurement rather than drawing new episodes.
  That is by the contract's design: the seeds are fixed.
- **The judge: the bar is met on every judged seed.** There were nine
  calls, all answered by claude-opus-5-5, none refused or retried, about
  $0.39 in all.

  | seed | medians (V1 V2 V3 V4) | total |
  |---|---|---|
  | 1101 | 3 3 3 3 | 12 |
  | 1105 | 3 3 3 3 | 12 |
  | 1110 | 2 3 3 3 | 11 |

- **The spec and the judge agree, so there is nothing to diagnose.** On
  1110, two calls scored V1 = 2 for visible wandering. The trace measures
  30 mm (0.58 COM heights), within B3. The predicate is authoritative
  (ADR-463), so this is recorded as a reading of the same fact, not a
  contradiction.
- **R3's measured bar is reached** by its pre-registered confirmation at
  the final revision. The owner ticks R3; I do not.
- The project committed its own evaluate row (`11f450d`, `cadex evaluate
  policy on balance_task → pass (r3-confirm-1)`).
- **Suites.** Only docs and retained JSON changed. The ot11 contract and
  judge tests pass: 32 passed. `pixi run python -m pytest cli/tests`: 1252 passed,
  1 skipped, as before. No engine, protocol, payload or trainer file changed, so no
  `test-engine` run or packaged gate was due.

**Concerns and assumptions.**

- **Assumption.** R3 does not require the IMU and encoder parts to be
  modelled. They are declared (ADR-408), as recorded in soft-otter-1938.
- **Sim-to-real (long-term rung).** The gyro channel reads in the world
  frame.
- **The P4 gap is unchanged.** Balance passed in one round, so P4's three
  motivated rounds still need another behaviour. Per the critic, reach is
  next, as P4's three-round proving ground (R2). That needs:
  - an arm copied into an `ot11-*` project;
  - a reach loop prompt like `prompts/balance.loop.prompt.txt`;
  - `rounds.py` driving it.
- No new dependency.
- The tail now has 2 unreconciled records.

Dispatch closed: 1 unit — R3 confirmation evaluation, pre-registered (c2dd99bb) then run once: policy 8919a22d passes the frozen balance spec on 10 of 10 seeds (none void) and meets the blind judge's bar on 1101/1105/1110 (12, 12, 11); spec and judge agree.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 413487bc307aa4ee4d4aabc1b095a0708164ada3

## State Impact

- target: staid-tooth-3475 — R3's pre-registered confirmation 1 (registration c2dd99bb, results 413487bc): policy 8919a22d on ot11-robin-1 passes B1-B5 on all ten frozen seeds, none void (worst: tilt 11.5 deg, drift 0.92 COM heights, heading 0.97 deg, recovery 0.42 s), and the blind judge's bar is met on 1101/1105/1110 with totals 12, 12, 11; spec and judge agree. R3's measured bar is reached; the owner ticks it.
- target: wild-harvest-4848 — Balance closed in one round, so P4's three motivated rounds still need another behaviour: reach (R2) is next as the three-round proving ground.
