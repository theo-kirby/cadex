---
node_id: 9c2135b0-496b-5b67-8f71-c7233ca213c0
slug: placid-bell-2440
title: 'orun2 D2: a design turn from the browser through cadex -p, its stderr the live transcript (ADR-504) — backfilled record'
created_at: '2026-10-03T17:30:25+00:00'
parents:
- morning-peak-8268
summary: ''
---
## What

Backfilled record for iteration 17's unit, which landed in commit `eb186a3d` (its message carries the slider's title because the slider's backfilled record rode in the same commit; the code in it is ADR-504). The unit was orun2 D2 item 1: a design turn started from the browser through `cadex -p`, with the child's stderr streamed to the page as the live transcript (ADR-504).

## Why

The critic's message for iteration 20 asked first for this record, causally parented, with its impact on D2 (`twilight-aspen-1541`). The unit landed without one, so it was invisible to the graph.

## Method

What `eb186a3d` changed (read from the commit and ADR-504, not re-done):
- `cli/cadex_cli/walk.py`: `run_leg(on_stderr=…)` gives the child a stderr pipe and hands decoded chunks to a callback; without one it behaves as before.
- `cli/cadex_cli/review_server.py`: `POST api/turn` (ADR-503 token + Origin check) takes `{"prompt", "resume"}` (non-empty, ≤16 000 chars, no NUL), runs `cadex --project <root> --prompt=<text> [--resume] --json` in a thread bounded at 3600 s and answers 202; `GET api/turn?since=N` returns the transcript after character N (capped at 4 MiB in memory), the state and, at the end, the envelope. One turn per project per server (409 otherwise).
- `review_static/`: `#turn-panel` starts turns, polls the transcript every second, refreshes the project when a turn ends (`docs/DASHBOARD.md` §19).
- `cli/tests/fake_claude.py`: a stand-in `claude` on `PATH` that speaks `stream-json` and calls tools over the real bridge.
- `cli/tests/test_dashboard_writes.py`: guard tests (403, 400, argv pinning, transcript offsets, 409 while running) and a headless-Chromium test against a real engine.

Re-verified this iteration at HEAD `6d1a1eb2`: `CUDA_VISIBLE_DEVICES= JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests/test_dashboard_writes.py cli/tests/test_comments.py -q -rs`.

## Result

- **D2 item 1 (start a turn, watch it live) is evidenced except for the image attachment.** In headless Chromium against a real engine, the page shows the agent's first words while the turn is still running and before it touched the engine, then draws the accepted revision at the new width, with the CLI's `PROGRESS.md` row and one project commit.
- Re-run at HEAD: `test_dashboard_writes.py` + `test_comments.py` **16 passed, 0 skipped** (17.1 s), browser tests running.
- The full CLI suite and `test-engine` results for iteration 17 were not written down by that iteration; this record does not invent them. Iteration 20's own record carries full-suite runs at its commit.
- **Gap kept open:** attaching an image to a prompt is not done — `cadex -p` has no way to carry an image into the turn yet (ADR-504 Cost). That is a CLI change first, then the page's.
- The transcript lives only as long as the server; a turn the server started is not cancelled by closing the page.

Dispatch closed: 1 unit — backfilled record for ADR-504's browser design turn with live transcript (commit eb186a3d); image attach still open.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 6d1a1eb286d260977d3f38986fff246a86abc0c0

## State Impact

- target: twilight-aspen-1541 — item 1 evidenced except image attach: POST api/turn runs cadex -p as a child behind the per-launch token, GET api/turn streams its stderr; headless-Chromium test against a real engine with a stand-in claude shows live transcript then the accepted revision drawn
