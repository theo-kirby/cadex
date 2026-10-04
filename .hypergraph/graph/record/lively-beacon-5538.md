---
node_id: 118fc823-0a0c-5d3b-8ec9-dc742fd68366
slug: lively-beacon-5538
title: 'orun2 C1: terminal turns keep transcript and looks on the page (ADR-526); defect 3 fixed'
created_at: '2026-10-04T06:21:46+00:00'
parents:
- clear-current-6218
summary: ''
---
## What

Recorded and evidenced the ADR-526 turn store (landed unrecorded in commit `d513f255`, iteration 55), and marked the closing report's defect 3 fixed. `cadex -p` keeps each turn under the project's self-ignoring `turns/<UTC stamp>-<hex>/` (`turn.json`, `transcript.txt`, one `look-NN-<view>.png` per picture the `look` tool gave the model, via a new `Bridge(on_look=…)` hook; `cli/cadex_cli/turn_store.py`). The CLI is the only writer (A3); `GET api/turn` answers a live page turn from memory and otherwise the newest stored turn (`source: "store"`), and the page shows the looks under the transcript (`#turn-looks`). `docs/probes/orun2/REPORT.md` §6 item 3 now reads "fixed (ADR-526)".

## Why

The critic's fix-first: write the missing record for ADR-526 with both suites' results (GPU hidden) and a State Impact on C1; add a Chromium test that a terminal turn's transcript and looks appear on the project page against a real engine; mark defect 3 fixed. That was the whole unit; the "next open defect" (defect 4) is left to the next iteration under the one-unit budget.

No new test was written, and that is a deviation from the critic's letter, not its intent: the test the critic asked for already existed in `d513f255` — `cli/tests/test_turn_store.py::test_browser_shows_a_terminal_turns_transcript_and_looks`. It runs the turn through the CLI's own `main(["--project", …, "--prompt=…", "--json"])` exactly as `./cadex -p` would at a terminal (not from the page), with a scripted fake `claude` that calls `write_script` and then `look` at `iso` and `top` against a real engine, then opens the project page in headless Chromium and asserts the stored-source transcript text, the tool lines, the accepted revision in the status, two decoded `#turn-looks` images with alts `look: iso`/`look: top`, a 200 PNG from the look URL, a 404 for `transcript.txt` by path, and that `git ls-files turns` in the project is empty. Verified it ran and did not skip (below), rather than duplicating it.

## Method

- `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests/test_turn_store.py -rs -v`: 5 passed in 7.29 s, no skips, the browser test included (`plate_app` depends on the real `engine` fixture).
- `pixi run test-engine`: **2607 passed, 56 skipped** in 410 s, exit 0.
- `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests -q -rs`: **1420 passed, 1 skipped** in 1274 s, exit 0. The one skip is `test_review_server.py:851` (needs `CADEX_REVIEW_HOST` set to a private-network address — the charter bars binding one), so every engine-needing CLI test ran.
- Edited REPORT.md §6 item 3 to state the fix, its ADR and its test.
- No protocol or payload change (ADR-526 touches neither `OP_ARG_SPECS` nor staging), so the packaged gate was not re-run this iteration.

## Result

True now: REPORT.md defect 3 is fixed with ADR-526, docs (`docs/CLI.md`, `docs/DASHBOARD.md`), unit tests of the store's bounds/refusals, and a real-engine headless-Chromium test of a terminal turn shown on the page; both suites are green at this tree with the GPU hidden. Open defects in the report: 4 (raw-NDJSON preview lane misses its own 0.10 s bar, median 0.763 s — not the slider's path), 5 (W1 step 7 on CPU; 5090 leg owner-blocked, no `nvidia` module), 6 (installed footprint unchanged; pixi audit deferred to next run). Next unit per the critic: defect 4.

Concern: the turn store was committed in iteration 55 as "no record"; this node is its record, parented on `clear-current-6218`. Reconcile tail is now this one node plus nothing else unreconciled.

Dispatch closed: 1 unit — ADR-526 turn store recorded with suite evidence; REPORT defect 3 marked fixed

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: d513f255d0a0295ac86bf9ceeaee4fe4b565dea8

## State Impact

- target: wild-ocean-3878 — REPORT.md defect 3 fixed by ADR-526 (turn store; real-engine Chromium test of a terminal turn's transcript and look images); both suites green GPU hidden (engine 2607 passed/56 skipped, cli 1420 passed/1 skipped); open defects now 4, 5, 6
- target: twilight-aspen-1541 — D2.1 watching a turn now covers turns started at a terminal: the page shows their stored transcript and look images (ADR-526)
