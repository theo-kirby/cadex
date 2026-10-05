---
node_id: 452738c4-eed3-51fc-b3d3-e494e06ea4a4
slug: tiny-bloom-2937
title: 'W1 gap 1 fixed: cadex mcp logs each call in flight, an in-flight evaluate reads as evaluating (ADR-553)'
created_at: '2026-10-05T15:14:18+00:00'
parents:
- solemn-fox-1118
summary: ''
---
## What

Fixed W1's product defect (gap 1 of `solemn-fox-1118`): an `evaluate` through `cadex mcp` was invisible on the page. Now `cadex mcp` writes an in-flight activity line when each tool call starts and a finished line with the same `call` id when it returns. An in-flight `evaluate` turns the overlay's stage to `evaluating`, and a call in flight shows as `running` in the activity line, never as `idle`. This is ADR-553, commit `fc86f7f8`.

## Why

The critic named this unit: an in-flight entry at call start, finalised on return, keeping ADR-549's bound, with an in-flight `evaluate` read as `evaluating`, no tool-surface change, a slow-call test through `cadex mcp` read back from `/api/project`, a browser test showing `evaluating`, an ADR and both suites with the GPU hidden. I did all of it. W1 is the highest-ranked open criterion, and this defect was what blocked its stage-by-stage claim at `evaluating`.

## Method

- `cli/cadex_cli/activity.py`:
  - `begin_activity` appends `{t: start, tool, args, outcome: "running", detail: "", ms: 0, call: "<pid>-<n>", pid}`.
  - `append_activity` takes `call=` and writes it on the finished line.
  - Both lines go through the same append and rotation, so ADR-549's 64 KiB / 32 KiB bound is unchanged.
  - `read_activity` reads newest first. A finished line hides its in-flight line. An in-flight line whose `pid` is gone (`os.kill(pid, 0)` gives ESRCH) reads `lost`.
- `McpSession.call` (`cli/cadex_cli/__main__.py`) calls `begin_activity` before `_open()`, so the session's engine open and build, which was about 68 s of W1's 68 s call, all counts as in flight.
- `review_server.py`:
  - `ReviewProject.review` now reads `activity` before `stage`.
  - `project_stage` adds `_evaluate_in_flight`. The newest `evaluate` entry, if it is `running`, gives the stage `evaluating`, reason "the agent's evaluate call is running", and `since` set to its start.
  - The `/api/project` keys are unchanged, so the ADR-552 contract is untouched.
- Page (`review.js`, `review.css`):
  - A newest `running` entry sets `data-state="running"`, and the line reads `<tool> <args> · running <duration>` in `--info`.
  - `lost` reads `· did not return` in `--bad`.
  - The `evaluating` stage line now adds how long the evaluation has been running.
  - `docs/DASHBOARD.md` §2 row, `docs/CLI.md` (the `cadex mcp` row and the test table) and ADR-553 are updated in the same commit.

## Result

**True now, measured:**
- `cli/tests/test_activity.py`, four new tests:
  - A call stays `running` until it returns and is then one finished entry.
  - A gone pid reads `lost`.
  - 2,000 two-line calls stay ≤ 64 KiB and read back as 10 finished entries.
  - **Real engine:** a `cadex mcp` process answers `evaluate` (first call of a fresh session on a plate project) while `/api/project` is polled over HTTP every 50 ms. The call is seen `running` with `stage.state == "evaluating"` and `since` equal to its start. Afterwards the same `call` is finished and the stage has moved on.
- `cli/tests/test_review_overlay.py`, two new tests:
  - The stage reads an in-flight `evaluate`, and does not read a finished, other or lost one.
  - **Browser** (Chromium through `browser.py`): an `evaluate` started 400 s ago and still running shows the chip `evaluating`, the line "the agent's evaluate call is running · 7 min", and the activity line `evaluate · running 7 min` in `--info`, past the idle threshold and not idle. When it returns, both turn back on the page's own poll.
- `test_project_tool_surface.py` is unchanged and passes. No tool, argument or result field was added.
- **Suites:**
  - `pixi run test-engine`: 2585 passed, 58 skipped.
  - `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`: 1172 passed, 1 skipped (the engine-needing tests ran; the engine is built).
  - No protocol or payload change, so no packaged gate is needed.

**Concerns and assumptions:**
- A call now costs two lines, so the capped log holds about half as many calls (roughly 75 to 250).
- `lost` relies on the pid being checkable on the same machine as the dashboard. That always holds today, because both read the local project directory. An unknowable pid reads as alive.
- An `evaluate` run as `cadex evaluate` outside `cadex mcp` is still seen only through its evaluation directory.
- **Next:** re-run W1 on `orun3-biped` with the driver picking `run:<run>` in `#view3d-source` when training starts (gap 2, a driver error), so that at least three checkpoint rollouts play live and `evaluating` is captured.
- No new dependency.

Dispatch closed: 1 unit — in-flight activity entries for cadex mcp calls; an in-flight evaluate reads as evaluating and a running call never as idle (ADR-553), tested through a real cadex mcp and a browser

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: fc86f7f80087b233862808b5ec34ae277d44f8ff

## State Impact

- target: lucky-prairie-0215 — gap 1 fixed (ADR-553, fc86f7f8): an MCP evaluate is now in flight in the activity log from its start and the stage reads evaluating for the whole call, tested against a real cadex mcp and in a browser; W1 still needs its re-run with the run picked in #view3d-source
