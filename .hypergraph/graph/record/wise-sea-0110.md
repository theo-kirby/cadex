---
node_id: 231ebe70-e9a6-5851-a754-368ba6f96a1c
slug: wise-sea-0110
title: 'ot10: A5 confirmation turn 1 — ot10-hexapod-11 meets the bar at 14/21'
created_at: '2026-09-28T19:24:02+00:00'
parents:
- honest-dawn-9522
summary: ''
---
## What

The first turn of the pre-registered A5 confirmation round: the frozen hexapod prompt on the new project `ot10-hexapod-11`. It was rendered by A2 from a `/tmp` copy, judged blind under the frozen A1 procedure (three calls), and published (commit `b2b40bff`). The publication has a README section, a score file, six renders and the concept sheet, all ≤300 KB. It also adds a REPORT row, the census entry in `refusals.json` and a contract test.

## Why

The critic asked for exactly this: run the pre-registered confirmation turn on ot10-hexapod-11 with the frozen prompt and argv, then render, blind-score and publish it either way. It serves A5 (`loyal-fountain-8709`). The turn had already been launched detached (`setsid`) at 2026-09-28T18:20:23Z, at revision `4288ef42`, just before the previous session's record. That launch used the frozen argv from `contract.json`. Its launch script, `started` and `launch_revision` receipts are in the notes directory. I did not start a second turn, because that would have been a duplicate attempt on the same plan. I waited for this one to exit. Between `96ed90d0` (the pre-registration) and `4288ef42`, only the README changed, so no product code changed.

## Method

- **Turn.** `CADEX_EFFORT=medium ./cadex --project ~/cadex-projects/ot10-hexapod-11 --model claude-opus-5-5 -p <a5.prompts.hexapod> --json`, with no continuation. It ended on its own at 19:01:35Z (41 min), exit 0 with `ok: true`, at accepted revision `42cbfa0dc717…` (digest `cc0e06aa9e55…`).
- **Render.** `cp -a` to `/tmp/ot10-hexapod-11`, then `./cadex render --project /tmp/...`, which wrote the hero, the proxies and the sheet. The notes-dir `look_views.py` drew the five `look` views.
- **Judge.** `runner/judge.py` on the hero plus the five look views.
- **Census.** `runner/refusals.py` `census()` on the session transcript. The transcript stays local and is not committed.
- **Tests.** `test_ot10_contract.py` and `test_ot10_report.py` were updated for the new row and the new census totals. There is a new test, `test_a5_hexapod_attempt_11_the_confirmation_round_is_published_with_its_score`. The two ot10 test files plus `test_part_sharp_edges.py` passed: 45 of 45.

## Result

**`ot10-hexapod-11` meets the A5 bar on every item.**

| bar item | measured |
|---|---|
| judged total | 14/21; all three calls identical at T1–T7 = 2, 3, 1, 2, 2, 2, 2; no trait at 0; above hex3's 2 |
| P1 | 0.0186 (3,685 of 197,646 subsamples) |
| P2 | 0.2285 (4,621 of 20,221 mm) |
| P3 | 3 (`#2B2D31`, `#E9E6DF`, `#F26A1B`) |
| static fit | 2,850 pairs, all clear; 0 intersections; only the floor's advisory world-geometry row; 62 fixed pairs touching |
| swept fit | complete and passing on 12 of 12 joints at 7° steps; 0 failing pairs |
| electronics | ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 12 × MG90S, 24 M2 screws |

- **Render.** Acquisition took 252.3 s; drawing took 11.1 s, with the 1024 px hero at 2.9 s. The concept sheet reads 0.618 kg, 12 servos, 227 × 231 × 116 mm.
- **Trait trade against attempt 10.** Same total by a different route: T2 rose to 3 and T6 fell to 2. T3 stays at 1 on both passing hexapods, so both hexapods sit exactly on the bar and are held back by joint treatment.
- **A4 census.** 12 refused calls, 0 in the four A4 classes and 0 CPU-limit refusals. The census now reads 0 of 195 across 15 transcripts.
- **New defect.** Three `edit_script` calls died with `DOMAIN_WORKER_NO_RESULT`. The agent attributes them to OCCT fillet SIGSEGV (`ChFi3d PerformThreeCorner`). The refusal does not name the operation. It is REPORT's defect 8 and was not fixed this iteration.
- **Not updated.** The REPORT's A5 verdict stays "not met by its letter", and its opening paragraph now says the round is in progress. `REPORT.md`'s C1 regression tables were not re-run: this change is docs and tests only. The full suites were not run this iteration.
- **Next, as pre-registered.** `ot10-quadruped-4` on the frozen quadruped prompt, with nothing changed, then `ot10-biped-2`. Launch it with `setsid nohup` and a turn.sh like `~/cadex-projects/ot10-notes/hexapod-11/turn.sh`, and copy its `pipeline.sh`.
- **Reconcile.** Unreconciled tail is now 3 records (`soft-cliff-8778`, `honest-dawn-9522`, this one), which meets the three-record reconcile trigger.

Dispatch closed: 1 unit — ot10-hexapod-11 confirmation turn run, scored 14/21, meets the A5 bar on every item, published

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: b2b40bffd7b31e12ba75efc1b3f6dd6992bb902a

## State Impact

- target: loyal-fountain-8709 — confirmation round turn 1: ot10-hexapod-11 (frozen hexapod prompt, launched at 4288ef42) meets the bar on every item: judged 14/21 (2,3,1,2,2,2,2, three identical calls), P1 0.0186, P2 0.2285, P3 3, static clean, swept complete and passing 12/12, electronics carried; commit b2b40bff; quadruped-4 and biped-2 still to run; A5 still not met by its letter for the first round
