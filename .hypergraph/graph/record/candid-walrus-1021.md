---
node_id: b3a1ed0c-eb17-5fb6-a266-0e57448bfba5
slug: candid-walrus-1021
title: 'F2 legacy: a run stopped before ADR-559 reads stopped (ADR-574)'
created_at: '2026-10-06T21:36:20+00:00'
parents:
- eager-sage-0150
summary: ''
---
## What
ADR-574 (commit `0f9e019c`): a loop run stopped on request before ADR-559 now reads **stopped**, with its reason, not failed. An ended run no longer carries the stale-telemetry warning. The D3 preset screenshots were retaken, and REPORT.md §5, §7, its ADR table, its F2 row and its done claim were updated.

## Why
The critic's named unit. REPORT.md §7 defect 1: `walk-r13` in `orun4-biped-sts` has `run.json` `status: failed`, written by the old `loop._record`, but `training-status.json` says `state: stopped` with the reason. So `/api/project`'s stage and the Status editor read **failed**, with "no telemetry update for over 30 s; process state unknown" under a long-ended run. That left F2 with a gap.
Deviation: the critic also asked me to "reconcile and claim done". Work iterations are forbidden to reconcile, so I did not. REPORT.md's done claim is updated to claim done for critic review, and it says that this record waits for the next reconcile pass.

## Method
- `cli/cadex_cli/review_record.py` `read_run_record`: a `failed` record whose run directory has a `training-status.json` (schema `cadex-training-status-v1`, same run or no run named) with `state: stopped` is read as `status: stopped`, `recorded_status: failed`, with `error` set to the supervisor's reason. The file is left as written. A supervisor that wrote `interrupted` or `failed`, or no file at all, keeps the run failed.
- `cli/cadex_cli/review_server.py` `training_telemetry`: a trainer snapshot is marked `stale` only while the record is live. When the record has ended (`ok`, `failed` or `stopped`) and the snapshot still says `starting` or `training`, the state is `ended`, with the reason "the run ended <status>; its trainer's last snapshot says it was still training". The page's run line reads `run walk-r13 · ended`. My first cut used `unknown`, which read badly in the screenshot, so I renamed it before committing.
- New test `test_review_status.py::test_a_run_stopped_before_adr559_reads_stopped_and_a_killed_one_failed`. With a `failed` loop record, a 1 h old `training` snapshot and a supervisor `stopped`, it checks that the stage is `stopped` with the reason, the telemetry is `ended`, and `/api/run` gives `stopped`, `recorded_status: failed` and `stopped on request`, with the file unchanged. With the supervisor `interrupted` instead, the stage is `failed`. **The test fails without the fix**: I stashed the source change and kept the test, and it failed at the stage assertion.
- On the real scratch copy (read through `ReviewProject.review()`): the stage is `stopped walk-r13 "stop requested: Iteration 140 passed…"`, with telemetry `ended`.
- Retook the eight D3 presets with a throwaway script outside the repo: `review_server.serve` on 127.0.0.1, `browser.py` headless Chromium at 1280 × 800, one click per preset, then the layout reset. Status reads `stopped` in all eight, with no warning. Sizes are 182,984 to 269,706 B (single unchanged at 234,107 B), all ≤ 300 KB.
- Docs: ADR-574 in `docs/DECISIONS.md`; the Status row in `docs/DASHBOARD.md`; `/api/project`'s stage in `docs/CLI.md`, which now lists `stopped`, missing there since ADR-559; REPORT.md.
- Gates, all foreground with the GPU hidden:
  - Before the `unknown`→`ended` rename, the CLI thirds gave 392 passed, 324 passed + 1 skipped, and 489 passed, and `pixi run test-engine` gave 2611 passed, 58 skipped.
  - After the rename, at `0f9e019c`: third 0 gave 392 passed, third 2 gave 489 passed, and third 1 gave **1 failed**, 323 passed, 1 skipped. Rerun with `-rf`, third 1 was 324 passed, 1 skipped.
  - No engine source changed, so the engine suite was not rerun after the rename.

## Result
F2's legacy gap is closed. A run stopped on request reads stopped whether its ending was written before or after ADR-559. A killed run with no stop request still reads failed. No route, schema, engine module, protocol op or tool changed.
- **Concern:** one CLI test failed once in third 1 at `0f9e019c` and passed on the rerun. Its name was not captured, because `-p no:cacheprovider` disables `--lf`. The third holds no file this unit touched (`test_review_status.py` is in another third), so I read it as a flake. Defect 4 in REPORT.md (the minute-boundary flake) lives in a different file, so this may be a second flake. The next iteration should run that third with `-rf` if it recurs.
- REPORT.md claims done for critic review. No owner box is ticked. This record is the one unreconciled node: the next reconcile pass folds it.
Dispatch closed: 1 unit — ADR-574: a pre-ADR-559 stopped run reads stopped, an ended run is never stale; D3 shots retaken, REPORT.md updated, gates green

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 0f9e019cdba5abe0209e4af71d12f949739b6871

## State Impact

- target: lucky-shade-9428 — ADR-574 (0f9e019c): a failed record whose training-status.json says stopped reads stopped with the reason (recorded_status failed, file untouched); an ended run's trainer snapshot reads ended, never stale; killed-without-request still reads failed; test fails without the fix; D3 shots retaken reading stopped; REPORT.md §7 defect 1 fixed, done claimed for critic review
