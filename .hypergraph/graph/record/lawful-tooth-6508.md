---
node_id: 8f57dd1f-3652-53b0-99ae-029e8b9b2e2e
slug: lawful-tooth-6508
title: 'ot10: C1 closing report — suites and packaged gate green, REPORT.md pinned to score files; done claimed for critic review'
created_at: '2026-09-28T17:44:08+00:00'
parents:
- true-grove-4773
summary: ''
---
## What
C1 for ot10: I ran both full suites and the packaged lifecycle gate at head `31de992c`. I wrote `docs/probes/ot10/REPORT.md`, the closing report, and added `cli/tests/test_ot10_report.py`, which ties the report to its receipts. Commit `26bc9ef0`.

## Why
The critic named C1 as the next unit, and I did what it asked with one exception. It asked me to "reconcile, then claim done", but a work iteration is forbidden to reconcile. So this record claims done for critic review and leaves the fold to the next reconcile pass. No owner box is ticked.

## Method
- I ran `pixi run test-engine`, `pixi run python -m pytest cli/tests`, and `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest test_cadexd_lifecycle.py`. First I compared the staged payload's `Mod/cadex/*.py` byte for byte against `src/Mod/cadex/*.py`. All 57 files match, so I did not rebuild.
- REPORT.md summarises `README.md` (the probe log) and the `*-score.json` files:
  - the instrument, and ADR-424, the one recorded change to it;
  - the before/after against hex3;
  - one table of every A5 attempt: 12 turns plus the hex3 baseline, each with its T1–T7 medians, total, P1–P3, static fit, swept fit, electronics and verdict;
  - the two aborted turns that are not attempts;
  - what each failure measured;
  - the renders, sheets and videos, with the A2 and W1 time bounds;
  - both W2 runs;
  - the A4 census;
  - the remaining defects;
  - the C1 results.
- The test has six checks:
  - every score file has exactly one row;
  - each row's medians and total equal its score file;
  - its P1, P2, P3, static, swept and electronics cells equal that attempt's gate table in the README;
  - each verdict is recomputed from `contract.json`'s bar, and the misses list must match exactly;
  - the counted set is {biped-1, quadruped-3, hexapod-10};
  - the census totals (14, 183) and the W2 verdicts are named;
  - every linked PNG is committed and 300 KB or less.
- I checked that the test fails on two mutations: a changed median, and a dropped miss.

## Result
- Engine suite: 2,242 passed, 53 skipped, 0 failed.
- CLI suite: 1,055 passed, 1 skipped, 0 failed.
- Packaged lifecycle gate: 23 passed.
- `test_ot10_report.py` 6/6 and `test_ot10_contract.py` 35/35, both run after the report was written.

Three designs meet the frozen bar: biped-1 at 15, quadruped-3 at 15 and hexapod-10 at 14, against hex3's 2. Nine attempts failed, and all are published. `w2-2` has `walked = true` under ADR-433, and `w2-1` has `walked = false`.

Concerns for the critic and the owner:
- **A5's literal clause.** The charter says "one failing design fails this criterion", and nine of twelve counted turns failed. The report publishes every attempt and leaves that reading to the owner. It does not claim A5 unconditionally.
- **Skip reasons.** I did not capture the reasons for the 53 engine skips (the run was `-q`).
- **Dashboard playback.** The Chromium playback check was not repeated for `w2-2`'s video.

Every open criterion A1–A6, W1, W2 and C1 now has evidence. I claim done for critic review, and no boxes are ticked. The unreconciled tail is now two nodes, `true-grove-4773` and this one. A reconcile is due before a second done acceptance can mean anything.

Dispatch closed: 1 unit — C1: suites green, ot10 REPORT.md written and pinned to the score files, done claimed for critic review

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 26bc9ef024b9838ce8f6c9fd36f3a5d406cb2226

## State Impact

- target: southern-prairie-3683 — C1 has evidence: at 31de992c test-engine 2242 passed/53 skipped, cli/tests 1055 passed/1 skipped, packaged lifecycle gate 23 passed on a payload matching source on 57 files; docs/probes/ot10/REPORT.md (commit 26bc9ef0) lists every A5 attempt, score, render, both W2 runs, the census and remaining defects, pinned by cli/tests/test_ot10_report.py; done claimed for critic review, owner boxes unticked
- target: loyal-fountain-8709 — REPORT.md tables all 12 counted A5 turns: biped-1 15, quadruped-3 15, hexapod-10 14 meet the bar; 9 failed attempts published; whether earlier failures count against the one-failing-design clause is left to the owner
