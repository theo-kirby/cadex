---
node_id: 314fd7f4-2bfa-578b-9685-279d490f9a1b
slug: morning-tooth-4242
title: 'ot10: A5 hexapod turn 13 — meets the bar at 15/21 on the ADR-439/440 engine; T3 2 vs hexapod-12''s 1; eleven misses stand'
created_at: '2026-09-29T05:10:54+00:00'
parents:
- smooth-ivy-2460
summary: ''
---
## What

The pre-registered A5 hexapod turn, `ot10-hexapod-13`, ran once on the ADR-439/440 engine. It was scored blind and published. **It meets the bar at 15 of 21.** It is the seventh design that meets the bar. Nothing is re-scored, so the eleven misses stand and A5 is still not met by its letter. Its T3 median is 2, against `ot10-hexapod-12`'s 1.

## Why

The critic named this unit exactly: run the frozen `ot10-hexapod-13` turn as registered, score it blind without changing anything, and publish the score, the renders, the sheet, the census row and the REPORT row. It serves `loyal-fountain-8709` (A5).

The critic's first fix was to correct the `loyal-fountain-8709` "Still open" line, which still says 16 turns and ten misses. That line is state-node text, and a work iteration may not edit state nodes. **I did not edit it.** This record's State Impact on `loyal-fountain-8709` carries the corrected count instead: at HEAD, REPORT.md counts eighteen turns and eleven misses. The next reconcile must fold it into that line.

## Method

- **Engine check.** Before launch I compared `build/release/Mod/cadex` with `src/Mod/cadex`. The Python is identical. Only `CMakeLists.txt`, `CadexGeometryWorker.cpp` and `cadex_tests` differ, and none of them is installed.
- **Launch.** Launched with `setsid` from `c245e539`, which differs from the pre-registration commit `deccf6d9` only in graph files. `turn.sh` is hexapod-12's script with only the project name changed. It reads `contract.json` `a5.prompts.hexapod`. The claude child's argv had `--model claude-opus-5-5 --effort medium`, and its environment had `CADEX_EFFORT=medium`. There was no continuation.
- **Turn.** Ran 04:06:53Z–04:38:21Z (31 min) and ended on its own with exit 0, `ok: true`. Accepted revision `59d8c5eb086d…`, digest `537a95dda09e…`, session `2e2bea8c…`.
- **Scoring.** Ran `cp -a` to `/tmp/ot10-hexapod-13`, then the notes `pipeline.sh`: `cadex render`, `look_views.py`, then `runner/judge.py` (3 blind calls, rubric sha `1c81caa2…`).
- **Census.** Ran `refusals.census()` on the transcript and inserted the row as `counted` after biped-3.
- **Published:**
  - the hero, five look views and the sheet, each 206 KB or less;
  - the score json, with no machine paths;
  - a README "A5 attempt 13" section and the census table and paragraph;
  - REPORT.md: the result paragraph, the attempts row, the before/after counts, the A5 clause (eighteen counted, eleven misses, seven meet), the sheets row, the A4 counts, and defects 1, 2 and 6.
- **Tests.**
  - New: `test_a5_hexapod_attempt_13_is_pre_registered_and_meets_the_bar`.
  - Updated: the census and report counts (18 scored, 231/20), the counted sets, and hexapod-13 at `("counted", 10, 0)`.

## Result

- **`ot10-hexapod-13` meets A5's bar.**
  - Judged 15/21, with medians 2/3/2/2/2/2/2. The three calls scored 14, 15 and 15.
  - P1 0.0031, P2 0.214, P3 3.
  - Static fit: 2,850 pairs, 0 intersections, 0 below clearance and 6 foot–floor contacts. The only failing row is the floor's advisory row. 62 fixed pairs, all touching.
  - Swept fit complete and passing, 12 of 12 joints.
  - Electronics: ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 12 MG90S with double-arm horns. A walking task is declared.
- **T3 is 2 in all three calls, against hexapod-12's 1.** That is one turn against one turn, with no causal claim. Every call still names the inconsistency between the dark hip caps and the cream knee discs.
- **The caps go over the horns.** The script sets `CAP_R = HORN_REACH + 1.6` with `HORN_REACH = 16.0`. Discs of that radius at the hip and the knee are cut with the horn body. 16.0 equals the catalog's `double_arm` `arm_reach_mm`, but the script writes it as a literal and does not read it from `.spec`.
- **Render.** This is the first A5 render under ADR-439. It used a 0.498 mm cell over the robot's 255 mm (floor excluded) and drew 231,405 of 978,992 triangles. Drawing took 12.1 s (hero 3.2 s) and acquisition 224.9 s.
- **Census.** 10 refused calls:
  - 0 CPU limit and 0 JSON pointer;
  - 2 sandbox;
  - 3 kernel;
  - 3 edit mismatch;
  - 2 `output_type` refusals.

  No A4 class recurred: 0 of 231 across 20 transcripts.
- **A5 by its letter.** Eighteen counted turns, eleven misses and seven that meet the bar. A5 is still not met by its letter, so the owner decides whether to accept it.
- **Per the critic, hexapod retries stop here.** The next units are W1/W2 or C1 closure.
- **Suites.** CLI 1075 passed, 1 skipped (the review-host skip). No engine or payload file changed, so the engine suite and the packaged gate were not re-run.
- **Nothing is broken.** The tail is one record since the reconcile.

Dispatch closed: 1 unit — ot10-hexapod-13 run once as pre-registered on the ADR-439/440 engine: meets A5's bar at 15/21 (T3 2 vs hexapod-12's 1; P1 0.0031, P2 0.214, P3 3; fits clean, swept 12/12, electronics); eighteen counted, eleven misses stand; loyal-fountain "Still open" count correction carried as an impact rather than a state-node edit

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 227195abc976db50239f8cb2e4cc0a84fc092956

## State Impact

- target: loyal-fountain-8709 — The pre-registered ot10-hexapod-13 turn (deccf6d9) ran once on the ADR-439/440 engine and meets the A5 bar at 15/21 (medians 2/3/2/2/2/2/2; P1 0.0031, P2 0.214, P3 3; static fit clean over 2,850 pairs; swept fit complete and passing 12/12; electronics carried), T3 2 vs hexapod-12's 1, caps 17.6 mm over the double-arm horns (commit 227195ab). Correct the Still open line: REPORT.md at HEAD counts eighteen turns, eleven misses and seven designs that meet the bar, so A5 stays not met by its letter and acceptance is the owner's call. Hexapod retries stop here per the critic; next is W1/W2 or C1 closure
