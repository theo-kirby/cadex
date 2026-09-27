---
node_id: 4a162989-57cd-53c0-bf88-3061e21bacee
slug: quiet-basin-1176
title: 'ot10 A5 hexapod attempt 2: 14/21 blind meets the judged bar, P1-P3 pass, swept fit incomplete (180 s sweep budget) so A5 missed; quadruped-2 launched'
created_at: '2026-09-27T21:58:56+00:00'
parents:
- late-glacier-7593
summary: ''
---
## What
Scored and published A5 hexapod attempt 2 (`ot10-hexapod-2`) in `docs/probes/ot10/README.md`. The commit adds the hero, the five look views, the raw judge replies (`ot10-hexapod-2-score.json`) and a contract test. After scoring, I launched the frozen quadruped prompt detached on the new project `ot10-quadruped-2` and committed its launch receipt.

## Why
Target: A5 (`loyal-fountain-8709`). I did exactly what the critic's message asked, in its order:
1. waited, polling, for PID 3606231 to exit, starting nothing new;
2. ran pipeline.sh (hero, five look views, three blind judges);
3. measured P1–P3 and the swept fit, and counted the A4 refusal classes;
4. published everything, and wrote the diagnosis;
5. only then launched the quadruped with setsid and nohup, and committed its receipt.

## Method
- **The turn.** It ended on its own after 39 min 14 s, exit 0. Accepted revision `996a0b7e7b90…`, digest `39be96a4b87a…`.
- **Scoring.** Ran `~/cadex-projects/ot10-notes/hexapod-2/pipeline.sh`: `cadex render` (in `/usr/bin/time -v`), `look_views.py` and `runner/judge.py`. judge.py makes three fresh calls, each seeing the rubric, the references and the candidates only.
- **Measurements.**
  - P1–P3 come from `review/render/summary.json` `proxies`.
  - The static and swept fit come from turn.json `fit`.
  - Electronics come from the inventory's `catalog_counts`.
  - Refusals come from `refusals.py` over the session transcript, and I read each refusal by hand.
- **Tests.** `cli/tests/test_ot10_contract.py`: 12 passed. It has a new test pinning attempt 2's score, its candidate hashes, and each image at 300 KB or less.
- **Quadruped launch.**
  - `CADEX_EFFORT=medium setsid nohup ./cadex --project ~/cadex-projects/ot10-quadruped-2 --model claude-opus-5-5 -p "<frozen quadruped prompt from contract.json>" --json`.
  - Started 2026-09-27T21:48:11Z at `b6c61073`.
  - PID 3670601 has parent 1 and its own session, and `CADEX_EFFORT=medium` is in its environment.

## Result
- **Attempt 2 misses A5 on one count: the swept fit is incomplete (12 of 12 joints unswept).** Everything else meets the bar.
  - Judged median **14/21**, which meets the frozen 14. The three calls gave 15, 14 and 14 and disagree only on T3 (2, 1, 1). Medians: T1 2, T2 3, T3 1, T4 2, T5 2, T6 2, T7 2. hex3 scored 2 and attempt 1 scored 13.
  - P1 **0.022**, P2 **0.088** (attempt 1: 0.655), P3 **3**.
  - Static fit: 1,953 pairs clear, 0 intersections. The only failing row is the advisory floor row.
  - Electronics: ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 12 × MG90S.
  - `cadex render`: 2 min 4 s in all, 58.5 s of it acquisition, 7.6 s drawing and 2.3 s for the hero.
- **CPU-limit refusals fell from 19 to 3.** This is ADR-418 measured on a real turn.
- **A4: none of the four classes recurred.** `refusals.py` tagged one refusal as horn style, but that is a false match on an output named `horn`. It was really the write_script drop-outputs guard. There were 10 refusals in all.
- **Diagnosis.** The agent declared 15° sweep steps, and the budget ran out on the first hip joint, so it turned the sweep off (project ADR-005, `docs/rejected.md`).
  - The limit is `_SWEEP_TOTAL_SECONDS = 180` in `cadex_assembly_worker.py`, with 90 s per joint. For 12 joints that averages 15 s per joint over 1,953 pairs.
  - `_bounded_sweep_call` also re-serialises every component's BREP for each joint.
  - No prompt can meet a complete sweep at this design size inside that budget.
  - **Next unit: a tool change, not a prompt change.** Profile one hip joint's sweep on a read-only copy of `ot10-hexapod-2` at `996a0b7e`, then make a 12-joint sweep fit. Candidates:
    - sweep only the pairs whose relative pose the joint moves;
    - cull by bounding box before `distToShape`;
    - serialise the BREPs once per sweep.
  - The weakest trait is T3: the hip yaw axes are uncapped.
- **Quadruped.** It is running detached on `ot10-quadruped-2`. Do not start another turn while PID 3670601 lives. Score it with the same steps: copy pipeline.sh and change the names.
- **Concern 1: the floor may count in P2.** The inventory's `printed_edges.measured` includes `c_floor`, which is world geometry. It may slightly inflate P2's denominator and sharp length. This does not change the verdict (0.088 against a 0.25 bar), but it is worth checking. I did not fix it in this unit.
- **Concern 2: `refusals.py` false-matches.** Its `horn|style` regex matches output names. It lives in the notes directory, not the repo.
- **Suites.** The full `cli/tests` run was started in the background, and its result was not seen before this record. This change is docs, one test and images only.
- The tail is now 2 unreconciled records.

Dispatch closed: 1 unit — A5 hexapod attempt 2 scored (14/21 blind, P1–P3 pass, swept fit incomplete → misses A5, diagnosed as the 180 s sweep budget); quadruped-2 launched detached with receipt

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 158e605a77d3edf53e5c27395b1b5fc327cc3da9

## State Impact

- target: loyal-fountain-8709 — hexapod attempt 2 (ot10-hexapod-2, 996a0b7e) scored 14/21 median (meets 14), P1 0.022 P2 0.088 P3 3, static fit clean, swept fit incomplete (agent turned sweep off after the 180 s _SWEEP_TOTAL_SECONDS budget ran out on the first hip at 63 components) so it misses A5; next is making a 12-joint sweep fit; quadruped attempt running on ot10-quadruped-2 since 21:48:11Z
- target: odd-tree-6681 — hexapod attempt 2 transcript: none of the four A4 refusal classes recurred (10 refusals; CPU-limit refusals 3, down from 19)
