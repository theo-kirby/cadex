---
node_id: 8163c8bd-dcf3-5cc8-9c52-acdd0dd70f3f
slug: first-journey-3938
title: 'ot10: hexapod attempt 7 judged 13/21, misses A5 on T3/T4; static fit and 12/12 sweep pass'
created_at: '2026-09-28T10:24:35+00:00'
parents:
- steady-aspen-0430
summary: ''
---
## What

A5 hexapod attempt 7 on the new project `ot10-hexapod-7`: the frozen cold
prompt (`contract.json` `a5.prompts.hexapod`), frozen argv, `claude-opus-5-5`,
`CADEX_EFFORT=medium`, design-only, no continuation. Rendered, scored blind
under the frozen procedure, published (commit `2f7cacba`) and diagnosed.
**Judged 13 of 21, under the frozen 14: a miss.** Every measured bar item
passes.

## Why

The critic's named next unit, after its fix-first item (the ADR-427
record, minted this iteration as `steady-aspen-0430`). A5
(`loyal-fountain-8709`) is the highest-ranked open criterion, and ADR-426/427
removed the two limits that made attempts 5 and 6 miss, so the hexapod had
to be re-run on unchanged frozen inputs to see what binds next.

## Method

1. **Launch.** `CADEX_EFFORT=medium ./cadex --project ~/cadex-projects/ot10-hexapod-7 --model claude-opus-5-5 -p <contract.json a5.prompts.hexapod> --json`,
   started 2026-09-28T09:36:19Z at `cafd3960` (engine `source: dev-tree`; every
   `src/Mod/cadex/*.py` byte-identical to `build/release`). It ended on its own at
   10:06:56Z (31 min), `ok: true`, accepted revision `f0a77bfb1936…`, digest
   `839d779f4627…`, one session `0bbcde0e…`. Receipts are in
   `~/cadex-projects/ot10-notes/hexapod-7/`: argv, started, ended, revision,
   turn.json, turn.stderr, refusals.txt and pipeline.sh.
2. **Measurement.** `cp -a` to `/tmp/ot10-hexapod-7`, then attempt 6's `pipeline.sh` with the name changed:
   `cadex render --json`, then `look_views.py`, then `judge.py` (3 calls, `claude-opus-5-5`,
   effort high, rubric sha `1c81caa2…`). Proxies came from `review/render/summary.json`, and the fit
   from the turn's `--json` envelope.
3. **Refusals.** `refusals.py` on the session jsonl.
4. **Diagnosis.** From the judges' reasons, the turn's DECISION/NOTE lines,
   its tool-call counts and the hero image.
5. **Contract test.** `test_a5_hexapod_attempt_7_is_published_with_its_score` pins the
   score file, each candidate's sha256 and the 300 KB cap, the median row
   and the README verdict line. It fails with the score file removed and
   passes with it: 19 passed.

## Result

- **Judged:** medians T1 2, T2 3, T3 1, T4 1, T5 2, T6 2, T7 2, **total 13**. The
  calls gave 12, 13 and 15. It is above hex3 (2), has no trait at 0, and
  is under the frozen 14. **A miss.** Attempts 5 and 6 scored 16 and 15.
- **Measured, all pass:**
  - P1 0.033 (5,125 of 157,257 subsamples); P2 0.247 (bar 0.25, 28
    printed components); P3 3.
  - Static fit: 1,653 pairs, 0 intersections, 0 below clearance, 6 feet
    resting on `c_ground` (advisory under ADR-427), and only the floor's
    own advisory row failing.
  - Sweep complete and passing, 12/12 at 17.5° steps; the busiest hip
    moves 357 of 1,653 pairs.
  - Electronics: ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 12 MG90S.
  - **This is the first hexapod whose accepted revision passes both fit
    halves.**
- **Render:** 6 min 55 s for the whole command: 202.7 s acquiring the
  tessellation and 8.2 s drawing, at 152,601 triangles. The test suites
  were running at the same time for part of it.
- **Diagnosis: T3 and T4.**
  - T4: the legs keep one `leg_thick` of 4.0 mm from hip to foot, so they
    taper in plan only.
  - T3: the knee discs read as horns, and the hip yaw axes show as bare
    shafts.
  - The graphite knee cradles `c_cx_*` are printed, `mechanism`-role boxes
    that follow the servo case with a 1.5 mm fillet. The judges read them
    as exposed servo cases, which P1 (3.3%) cannot see.
  - The build budget crowded out refinement: one CPU-limit refusal. The
    agent dropped the loft-edge fillets "when the first full build ran out
    of CPU time", coarsened the sweep to 17.5° because a 10° step "ran
    past the 300 CPU-second limit", called `look` only twice and accepted
    after 31 min (attempt 5 took 85).
- **A4:** none of the four refusal classes recurred. There were 9 refusals:
  1 CPU limit, 3 guessed pointers, 1 `dir` sandbox, 1 import policy, 1
  `loft_cage` argument, 1 reset-tilt task refusal, and 1 `edit_script`
  miss.
- **Quadruped:** not rerun. quadruped-3's static fit was already clean and
  its sweep was already complete and passing (8/8). ADR-426 and ADR-427
  only turn refusals and failures into measurements or advisories, so
  under both its verdict still stands.
- **Assumption and concern:** the sweep's share of the accepted build's
  CPU comes from the agent's own words and is **not measured**. **Next
  unit:** measure it on a `/tmp` copy of `f0a77bfb` (the build's CPU at
  17.5° and at 10° sweep steps, and with the sweep off) before any
  overlay, budget or sweep change. The 300 CPU-s build limit now trades
  directly against refinement.
- The A5 tally for the hexapod: 7 attempts, 0 meeting the bar. The
  quadruped (3) meets it. The biped (1) has not been re-attempted.
- The tail holds 2 unreconciled records, this one and `steady-aspen-0430`.
- Suites at `cafd3960`: engine 2239 passed, 53 skipped; CLI 1012 passed, 1
  skipped. This unit changed only docs, a PNG set, a score file and one
  contract test (19/19 pass).

Dispatch closed: 1 unit — ot10 hexapod attempt 7 judged 13/21 (misses the frozen 14 on T3/T4) with every measured item passing; diagnosed as constant-section legs, servo-shaped graphite cradles and CPU budget crowding out refinement.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 2f7cacba4af5256910c28f33bc31b1be1930a8c7

## State Impact

- target: loyal-fountain-8709 — hexapod attempt 7 (ot10-hexapod-7, f0a77bfb) judged 13/21 < 14: miss. Every measured item passes (P1 0.033, P2 0.247, P3 3, static fit clean with 6 advisory floor contacts, sweep 12/12 at 17.5°): the first hexapod clean on both fit halves. Diagnosis: constant-section legs, servo-shaped graphite cradles read as exposed servos (P1 blind to it), and the 300 CPU-s build limit crowded out refinement (unmeasured; next unit measures the sweep's CPU share). A4 classes did not recur. quadruped-3 still meets the bar under ADR-426/427; not rerun.
