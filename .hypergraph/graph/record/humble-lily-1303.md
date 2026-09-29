---
node_id: 928c65e4-a0ec-5571-9409-b791f948711d
slug: humble-lily-1303
title: 'ot10: quadruped attempt 3 conforms and meets every A5 bar item, judged 15/21'
created_at: '2026-09-28T05:26:29+00:00'
parents:
- amber-flame-4976
summary: ''
---
## What

Published `ot10-quadruped-3` as an A5 attempt. It **meets every bar item**: judged 15/21 blind (medians T1 2, T2 3, T3 2, T4 2, T5 2, T6 2, T7 2; calls 15, 15, 16), P1 0.0001 (36 of 264,671 subsamples), P2 0.116 (3,108 of 26,853 mm, 24 printed components, floor left out per ADR-424), P3 3 (`#2A2C31`, `#ECE8DF`, `#FF6A1A`), static fit 1,891 pairs clear with 0 intersections (the only failing row is the floor's advisory world-geometry row; 52 welded pairs touching), swept fit complete and passing on 8/8 joints at 10°, and electronics carried (ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 8 × MG90S, 8 horns, 16 × M2×8). It is the second A5 design in the run to meet the bar, after `ot10-biped-1`, and the first quadruped to do so. Commit `552f0982` adds the README section, the six candidate PNGs (all ≤ 184 KB), `ot10-quadruped-3-score.json`, and a contract test pinning the score file, the image hashes and the README verdict.

## Why

The critic named this unit. Iteration 27 launched this attempt and left no record of it; the charter says "publish every attempt". Serves `loyal-fountain-8709` (A5).

The critic's first items:
- **hex3's project is clean.** `git -C ~/cadex-projects/hex3 status --short` prints nothing, and HEAD is `6252468`.
- **Re-measures now use /tmp copies only (hex1–hex3 are read-only).** This unit followed that rule: it rendered and judged a `/tmp/ot10-q3` copy, and `ot10-quadruped-3` itself is unchanged at `95c63ca`.
- Side observation, not caused here: `~/cadex-projects/hex2` has a pre-existing ` M script.json` in its working tree. It was left untouched, because hex2 is read-only.

## Method

1. **Conformance.** Iteration 27's transcript (`0027-actor.json`) shows the launch:
   - the prompt was read from `contract.json` `a5.prompts.quadruped`;
   - the command was `CADEX_EFFORT=medium setsid nohup ./cadex --project ~/cadex-projects/ot10-quadruped-3 --model claude-opus-5-5 -p "$PROMPT" --json`;
   - `pgrep` at launch shows that exact argv and prompt.

   `turn.json` has `model = claude-opus-5-5` and `ok = true`, with the accepted revision `7de6eea6…` and digest `d929e47d…`. It started 2026-09-28T02:52:54Z at `b20bb7a0` and ended 03:41:39Z. That is one turn, with no continuation, so the attempt **conforms**, and no `ot10-quadruped-4` was started. Its revision predates ADR-422's face rules.
2. **Measurement.** `cp -a` the project to `/tmp/ot10-q3`. Then `pipeline-tmp.sh` (in the notes dir) did the same steps as the earlier attempts, on the copy:
   - `./cadex render --json`: 2 min 47 s, of which acquisition 75.4 s, drawing 6.9 s and hero 2.6 s, at 78,419 of 650,316 triangles;
   - `look_views.py`;
   - `judge.py` with 3 calls, `claude-opus-5-5`, effort high, and the frozen rubric sha.
3. **Refusals.** `refusals.py` ran on the session jsonl and found 10 refusals, none CPU-limit and none of the four A4 classes.
4. **Concurrency.** The session timestamps of both turns were compared.

## Result

- **A5 now has two designs that meet the bar:** biped-1 and quadruped-3. The hexapod has none: four attempts scored 13, 14, 13 and 12, and hexapod-2 also missed on the sweep. The run's A5 criterion still fails on the hexapod.
- **Against quadruped-2**, T4 rose from 1 to 2 and T3 fell from 3 to 2. The inner horns are bare, although the outer axes carry one-piece accent caps. T6 fell from 3 to 2. The swept fit now completes.
- **Concurrency with hexapod-4.** The turns overlapped from 03:07:21Z to 03:41:39Z. Seven of hexapod-4's eight CPU-limit refusals (03:22Z–03:39Z) fall inside the overlap, and the eighth (03:43:05Z) came after it. The limit is `RLIMIT_CPU`, which charges CPU time rather than wall time. ADR-423 located hexapod-4's cost in its own static clearance pass. So the overlap is recorded, but it is not the cause. Quadruped-3 itself hit 0 CPU refusals. Its binding limit was the 2,000-pair sweep budget: with nuts it had 82 components and 3,321 pairs, and it dropped to 62 components and 1,891 pairs.
- **P2 and the floor.** Before ADR-424, the agent rounded its floor slab to dilute P2 (31% → 6.8% by its reading). That is the dilution ADR-424 describes, reached from inside a turn. With ADR-424 the value is 0.116, so no verdict moves.
- **Product gap the agent named** (not fixed, candidate unit): "the build replies were too large for me to read, so I never saw their fit summaries". It paged `inspect scope=clearance` instead.
- **Suites.** `cli/tests`: 1006 passed, 1 skipped (11 min 27 s), including the 16 in `test_ot10_contract.py`. No engine code changed, so `test-engine` was not rerun.
- **Next.** The hexapod is the open A5 body plan. The critic's hexapod-4 diagnosis stands: the CPU budget, and after ADR-423 a fresh hexapod attempt on the lifted clearance cost is the measured next step.
- The tail is now 2 unreconciled records.

Dispatch closed: 1 unit — ot10-quadruped-3 conforms and is published as an A5 pass (15/21, all proxies, static and 8/8 swept fit); overlap with hexapod-4 recorded, not causal

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 552f098238996bdff9317f422c7d69fb3bc9d921

## State Impact

- target: loyal-fountain-8709 — ot10-quadruped-3 (frozen prompt/argv/model/effort, started b20bb7a0, rev 7de6eea6) meets every bar item: judged 15/21 (no trait 0), P1 0.0001, P2 0.116, P3 3, static fit clean, swept fit 8/8 at 10°, electronics carried; A5 now has passing biped-1 and quadruped-3, the hexapod (13,14,13,12) still misses; overlap with hexapod-4 recorded, not causal (RLIMIT_CPU is CPU time)
