---
node_id: 962461ec-3bbc-51b7-8ac4-85a19c8d8b9a
slug: tidy-banner-2442
title: 'ot10: A5 biped turn 3 — ot10-biped-3 meets the bar at 14/21 on the ADR-434 engine'
created_at: '2026-09-28T22:11:14+00:00'
parents:
- civic-falcon-6725
summary: ''
---
## What

A5's biped turn 3. I pre-registered it (commit `e24ff330`), ran it once on the new project `ot10-biped-3` on the ADR-434 engine, scored it blind under the frozen procedure, and published it. **It meets the bar on every item.**
- **Judged total:** 14 of 21, exactly the bar. Medians T1–T7 are 2/2/2/1/3/2/2, and the three calls scored 15, 15 and 14.
- **Proxies:** P1 0.0035, P2 0.2214, P3 3.
- **Static fit:** 2,485 pairs, 0 intersections, 0 below clearance. 63 fixed-joint pairs, all touching.
- **Swept fit:** complete and passing, 6 of 6 joints, 0 failing pairs.
- **Electronics:** ESP32, PCA9685, BNO085, D36V50F6 and a 2S LiPo, with MJCF and a walking task accepted.

## Why

The critic named this unit: pre-register a new frozen biped turn on `ot10-biped-3` (frozen prompt, `claude-opus-5-5`, `CADEX_EFFORT=medium`), state that the round's ten misses stand and nothing is re-scored, run it on the ADR-434 engine, score it blind, and publish the score file, renders and census row. It targets `loyal-fountain-8709` (A5), the highest-ranked open criterion. I did exactly what was asked, with no deviation. The rubric, bar and judge are untouched.

## Method

- **Pre-registration.** `docs/probes/ot10/README.md` has a new section, "A5 biped turn 3, pre-registered", committed at `e24ff330` before launch. Before launch I compared installed `build/release/Mod/cadex` file by file with `src/Mod/cadex` and found them identical. The turn itself used the dev-tree engine (`src/Mod/cadex`, per `render.json` `engine.source`), which carries ADR-434.
- **Turn.** `~/cadex-projects/ot10-notes/biped-3/turn.sh` is biped-2's script with the name swapped. It reads the prompt from `contract.json` `a5.prompts.biped` and runs `./cadex --project … --model claude-opus-5-5 -p … --json` with `CADEX_EFFORT=medium`. It was launched with `setsid` at 21:13:33Z. The process list showed `--model claude-opus-5-5 --effort medium`, and the child environment had `CADEX_EFFORT=medium`. It ended on its own at 21:48:55Z (35 min), exit 0, `ok: true`, at accepted revision `f4095410c2b2…` (digest `d8c4cade1ff6…`), session `7970c27b…`.
- **Scoring.** I copied the project with `cp -a` to `/tmp/ot10-biped-3` and ran the notes `pipeline.sh`: `cadex render` (3 min 7 s wall; 82.0 s acquisition, 8.2 s drawing), then `look_views.py`, then `runner/judge.py` (three blind `claude-opus-5-5` calls, rubric sha `1c81caa2…`). The project itself is untouched. The proxies come from `review/render/summary.json`. Fit and inventory come from the turn's own `--json`.
- **Census.** I ran `runner/refusals.census()` on the session transcript, inserted the result as `counted` after `ot10-quadruped-4`, and regenerated the table. The transcript has 5 refusals, none of them in A4's four classes: 2 sandbox, 1 kernel, 1 JSON pointer and 1 reset-variation. Across 18 transcripts, 0 of 213 refusals fall in A4's four classes.
- **Published** under `docs/probes/ot10/`:
  - the hero, five look views and the sheet, all ≤ 114 KB;
  - `ot10-biped-3-score.json`, with no machine paths;
  - a README section, "A5 attempt 3: the biped (`ot10-biped-3`)", with the score table, bar table, render description, how the turn got there, and its refusals;
  - an updated census paragraph and table;
  - in REPORT.md: the attempt row, the result paragraph, the A5 verdict paragraph (ten misses stand, nothing re-scored), the before/after table, the sheets row, the census numbers, and remaining defects 1–3 and 6.
- **Tests.** A new `test_a5_biped_attempt_3_is_pre_registered_and_meets_the_bar`, plus updated census and report counts (16 scored, 6 counted, 213/18). `test_ot10_contract.py` and `test_ot10_report.py`: 45 passed.

## Result

- **`ot10-biped-3` meets the A5 bar at 14, with T5 at 3**, the first 3 on face for any counted biped. This is a second biped that meets the bar.
- **Weakest trait:** T4 is 1 in all three calls. The head is well rounded, but the legs are stacked servo blocks under shell lids, with flat brackets and plate feet. T1 and T6 are 2 for the same legs.
- **The agent's own notes** flag two things. Build replies overflowed the tool limit at about 200 outputs, so it read the fit by paging `inspect scope=clearance`. It also put the MJCF and task export behind an `export_task` switch.
- **The ADR-434 fix held in use:** no publish was refused mid-pass, and no write wedged.
- **A5 by its letter stays not met.** The ten misses stand, and the confirmation round stays closed at 2 of 3. I do not decide done, and the owner ticks the box.
- **Nothing is broken** that I know of.
- **CLI full suite:** 1065 passed, 1 skipped. No engine code changed, so the engine suite and the packaged gate were not re-run.
- **Concerns for the next iteration:**
  - The oversized build reply, at about 200 outputs, costs the agent turns. It is a measured candidate for the next tool unit.
  - The score sits exactly at the bar, so it has no margin.

Dispatch closed: 1 unit — ot10-biped-3 pre-registered, run once on the ADR-434 engine and scored blind: meets the A5 bar at 14/21 (P1 0.0035, P2 0.2214, P3 3, clean static and complete swept fit, electronics); published with census row; ten misses stand, nothing re-scored

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 98decddbb4fb69a1192679c78f05305124ab0a65

## State Impact

- target: loyal-fountain-8709 — A pre-registered biped turn (e24ff330) ran once on new project ot10-biped-3 on the ADR-434 engine and meets the A5 bar: judged 14/21 (medians 2/2/2/1/3/2/2, T5 3), P1 0.0035, P2 0.2214, P3 3, static fit clean (2,485 pairs), swept fit complete and passing 6/6, electronics with MJCF and task; published with score file, renders, sheet and census row (0 of 213 A4-class refusals across 18 transcripts), commit 98decddb. Nothing re-scored: the confirmation round stays 2 of 3 and the ten misses stand, so A5 by its letter remains not met; counted designs meeting the bar are now six (two per body plan)
