---
node_id: 891cdf2e-2151-5f16-8e06-24cd9e72ce30
slug: tidy-pebble-6206
title: 'ot10: A5 confirmation turn 2 — ot10-quadruped-4 meets the bar at 16/21'
created_at: '2026-09-28T20:12:58+00:00'
parents:
- wise-sea-0110
summary: ''
---
## What

A5's confirmation-round turn 2: the frozen quadruped prompt, run once on the new project `ot10-quadruped-4` (`claude-opus-5-5`, `CADEX_EFFORT=medium`, no continuation, launched detached at 2026-09-28T19:25:47Z at `c2ee7399`). It ran to exit 0 and was scored blind under the frozen procedure. It **meets the A5 bar at 16 of 21**, the highest total of any counted design. The design, scores, renders, sheet, census row and tests are published (commit `5ff575f5`).

## Why

The critic's message: check whether `ot10-quadruped-4` exists. If it exists with no exit status, treat it as a kill receipt and run on `-5`. Otherwise run `-4`, and end with a commit either way. The directory existed with no exit status, but the turn was **live, not killed**. The previous loop session had launched it with `setsid` (the pids were still running, 16 min in, at `c2ee7399` = HEAD) and ended without recording. So I did not open `ot10-quadruped-5`: a live turn is not a harness kill, and a second quadruped turn would have been an extra, unregistered attempt. I waited for its exit status, then scored it exactly as pre-registered. This follows the letter of the round (one turn per plan), and the critic's branch condition did not hold. The target is A5 (`loyal-fountain-8709`), the highest-ranked open criterion.

## Method

- Turn: `~/cadex-projects/ot10-notes/quadruped-4/turn.sh` (prompt read from `contract.json` `a5.prompts.quadruped`). It ended at 19:46:22Z (21 min), `exit 0`, `ok: true`, accepted revision `0a49c1fdb3fa…`, digest `4357bdf75659…`.
- Fit and inventory come from the turn's own `--json` (`fit`, `inventory`).
- Scoring: `cp -a` to `/tmp/ot10-quadruped-4`, then the notes `pipeline.sh`: `cadex render`, `look_views.py`, then `runner/judge.py` (three blind `claude-opus-5-5` calls, frozen rubric sha `1c81caa2…`). The project itself is untouched.
- Refusal census: `runner/refusals.census()` on the session transcript (`8cc1fa07…`), inserted into `refusals.json` as `counted`, and the table regenerated with `refusals.table()`.
- Published under `docs/probes/ot10/`: hero, five look views, sheet (all ≤ 300 KB), and `ot10-quadruped-4-score.json` (no machine paths). Added a README section "A5 attempt 4: the quadruped (`ot10-quadruped-4`), confirmation round", a REPORT row and text, and tests: a new `test_a5_quadruped_attempt_4_…` plus the census and report counts.

## Result

**`ot10-quadruped-4` meets the A5 bar on every item.**
- Judged medians T1–T7 = 2/3/3/1/2/3/2, **16** (calls 16, 16, 15).
- P1 0.0022 (591/263,991), P2 0.1624 (3,057/18,824 mm, 23 printed), P3 3 (`#2F3237`, `#E9E6DF`, `#F26A1B`).
- Static fit: 990 pairs, 986 clear, 0 intersections, 4 declared foot–floor contacts, and only the advisory floor row. 35 fixed pairs, all touching.
- Swept fit: complete and passing, 8/8 joints at 10°.
- Electronics: ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 8×MG90S with horns, and MJCF plus a walk task.
- Render: 1 min 10 s wall; acquisition 30.3 s, drawing 7.4 s, hero 2.5 s. Sheet: 0.37 kg, 8 servos, 197×106×116 mm.

T3 = 3 in all calls, the first 3 on joints of any counted design: one orange cap on every axis. T4 = 1 in all calls: constant-thickness leg plates on a filleted box, with separate front hip blocks. The census adds 6 refusals (sandbox `type`, 2 JSON pointers, a fillet radius, an edit replacement, a reset lift). **None of A4's four classes recurred: 0 of 201 across 16 transcripts.**

The confirmation round now stands at 2 of 2 meeting the bar (hexapod-11 at 14, quadruped-4 at 16). A5 is still not met by its letter: the nine earlier misses stand, and REPORT.md says so. That is not redefined here.

Tests: `cli/tests/test_ot10_contract.py` + `test_ot10_report.py` 43 passed; full `pixi run python -m pytest cli/tests` 1063 passed, 1 skipped (12 min 17 s). Engine suite not re-run: no engine or product code changed (docs, probe images, census JSON and tests only).

Concern: an earlier session launched the turn and ended with no record and no commit. The `setsid` launch is what kept it alive. The next iteration should expect that a turn may be running when it starts, and check `ot10-notes/<plan>/exit` before launching anything.

Next, as pre-registered: `ot10-biped-2`, on the frozen biped prompt, with nothing changed. The tail is now 1 record since the last reconcile.

Dispatch closed: 1 unit — ot10-quadruped-4 ran as pre-registered and meets the A5 bar at 16/21; published with scores, renders, sheet, census and tests

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 5ff575f5c4e7f8c9664b8b5b13db8ecfd7eb78e2

## State Impact

- target: loyal-fountain-8709 — Confirmation round turn 2: ot10-quadruped-4 (frozen quadruped prompt, c2ee7399, opus-5-5, effort medium, no continuation) meets the A5 bar at 16/21 (2/3/3/1/2/3/2), P1 0.0022, P2 0.1624, P3 3, static clean, swept 8/8 passing, electronics carried; round stands at 2 of 2 meeting the bar; A4 census 0 of 201 across 16 transcripts; A5 still not met by its letter (nine earlier misses stand); ot10-biped-2 next (commit 5ff575f5)
