---
node_id: 7eb3b765-e2b3-53ec-96ee-a794e2d1e871
slug: fond-dawn-4115
title: 'GUI parity slice 1: the studio renderer is engine code, run beside the service (ADR-445)'
created_at: '2026-09-29T10:05:15+00:00'
parents:
- warm-spire-8762
- keen-comet-6140
summary: ''
---
## What

GUI-parity slice 1 (ADR-445): the studio renderer, the concept sheet and the dark scene palette moved from `cli/cadex_cli/{render,sheet,scene}.py` into the engine as one module, `src/Mod/cadex/CadexStudio.py`, unchanged in what they draw. The look's facts moved with them (`CadexStudio.look_report`). `sheet.py` and `scene.py` are deleted; `render.py` keeps only the client half of `cadex render`.

## Why

The owner chose one implementation for the CLI and the app. An engine **op** was measured out: cadexd dispatches serially and a render is ~12 s (ot10 probes: 12.2–13.0 s), which would stall a slider drag queued behind it. The shell may not import cadex code, so it gets a process boundary.

## Method

- Moved code by a script (split, strip module prefixes), not a rewrite; renamed the renderer's index colours `INDEX_PALETTE` where they clashed with the scene `PALETTE`.
- CLI loads the module by path (`cli/cadex_cli/studio.py`, the `protocol.py` precedent). The shell's entry is `python Mod/cadex/CadexStudio.py REQUEST.json` → one JSON line, schema `cadex-studio-request-v1` / `cadex-studio-result-v1`, documented in `docs/INTEGRATION.md`.
- The palette source inverted: the engine's literal table is the source; `review_static/environment.js` and `review.css` are held equal to it by `cli/tests/test_scene_palette.py` (the regex reader and its two tests are gone).
- New `cadex_tests/test_studio_process.py`: look and render through the process entry, process look == in-process look, refusals, `CadexStudio` outside the service closure, installed by CMake.
- Baseline: clean `main` (680a217c) in a `git worktree`, CLI suite with `CADEX_ENGINE_ROOT` at the staged payload, full failure list kept; branch run the same way; failures diffed.

## Result

- `pixi run build-engine && pixi run stage-engine`: payload carries `Mod/cadex/CadexStudio.py`; the payload's own `bin/python` (3.11.14) runs it (exit 2 on an unreadable request, as specified).
- Engine suite: 2286 passed, 54 skipped (main: 2281 passed; +5 new tests).
- CLI suite: branch 52 failed / 1024 passed / 2 skipped / 7 errors vs main 51 / 1019 / 9 / 7. The failure-list diff is one test, `test_walk::test_the_walk_takes_the_toy_to_a_verified_rollout_and_iterates`, which main **skipped** (the baseline worktree has no `.venv` trainer) and which fails on the branch at the same broken Chromium as every other browser test — not a regression.
- Environment, not code: on this Mac mini `/opt/homebrew/bin/chromium` points at a missing `/Applications/Chromium.app`, so all browser-driven CLI tests fail on main too. `pixi run gate` on clean main reports `ok: false` with 8 failures, all the restore-failed lockout scenario; untouched by this change (no `shell/` diff).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: gui/studio-in-engine
- commit: 680a217c09255649f6642d2b02b9cdf212458c8b

## State Impact

- target: forest-wind-0342 — the engine now owns the studio renderer, concept sheet, scene palette and look facts (CadexStudio.py, ADR-445): outside the service closure, shipped in the payload, run by the shell as a child process via cadex-studio-request-v1; no protocol change
- target: chilly-union-8972 — the CLI draws with the engine's CadexStudio loaded by path (cli/cadex_cli/studio.py); sheet.py and scene.py deleted; the dashboard's palette files are test-held equal to the engine's table
