---
node_id: 7814349b-c0a0-5e24-8c15-7ac093448d39
slug: morning-peak-8268
title: 'orun2 D2: the slider write through cadex params, behind a per-launch token (ADR-503) — backfilled record'
created_at: '2026-10-03T16:46:50+00:00'
parents:
- mild-grove-9448
summary: ''
---
## What

Backfilled record for iteration 16's unit, which landed as commit `6eaeedeb` ("ouroboros #16: no record") without a record node. The unit was orun2 D2's first write: a parameter slider on the dashboard that runs `cadex params` as a child, behind a per-launch token and an Origin check (ADR-503).

## Why

The critic's message for iteration 17 asked first for this record, parented on `mild-grove-9448`, with its impact on D2 (`twilight-aspen-1541`), the measured slider p50/p95 beside the raw-NDJSON bar from `cadexd_latency_integration.py`, and the suite results. An unrecorded unit is invisible to the graph; this makes it visible. Done as asked.

## Method

What `6eaeedeb` changed (read from the commit, not re-done):
- `cli/cadex_cli/review_server.py`: `POST api/params` under `/` (`cadex review`) and `/p/<name>/` (`cadex app`). Body `{"values": {name: number}}`; names must be identifiers and values finite numbers. It runs `cadex params --project <root> --set NAME=VALUE ... --json` through `walk.run_leg` with a 300 s bound and no `--wait`. Replies 200/400/422/409 from the child's exit. Every POST is checked before routing: `X-Cadex-Token` must equal the launch's `secrets.token_urlsafe(32)`, written into the served `index.html`'s `<meta name="cadex-write-token">`, and an `Origin`, when present, must equal `Host`.
- `review_static/`: each declared number with a finite range is a slider on the accepted view; one release is one write; the following poll reloads the model.
- `cli/tests/test_dashboard_writes.py`: no-engine guard tests (403 without/with a wrong token, from another origin, before routing, spawning nothing), argv pinning, malformed bodies, a refused child as 409, and a real-engine headless-Chromium test that moves the slider five times.
- Docs: ADR-503, `docs/DASHBOARD.md` §18, `docs/CLI.md`, `docs/ARCHITECTURE.md`.

Measurements taken this iteration, on the dev tree on sb1x, at the clean `6eaeedeb` tree:
- `CUDA_VISIBLE_DEVICES= JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests/test_dashboard_writes.py -s`
- `pixi run python src/Mod/cadex/cadex_tests/cadexd_latency_integration.py`

## Result

- **Slider latency, one-box plate, headless Chromium, n=5 releases:** slider release to rebuilt model drawn **p50 582 ms, p95 636 ms**; the `cadex params` child alone p50 0.53 s, p95 0.54 s. A second run later in the iteration: p50 596 ms, p95 669 ms (child p50 0.58 s, p95 0.62 s). ADR-503 itself cites an earlier n=20 run (p50 548 ms, p95 556 ms); the test as committed runs n=5.
- **Raw-NDJSON bar, same machine, same session (`cadexd_latency_integration.py`, 10 drags):** warm `set_params` median **0.381 s**; with display **0.482 s**, inside its **0.65 s** parity bar. So the slider's cold-child path costs about 0.1–0.2 s over the warm raw request with display on this model.
- The latency script's overall `ok` is **false**, as before this unit: its preview lane median is 0.766 s against a 0.1 s preview bar, and its live lane is skipped (no `CADEX_LIVE_PROJECT`). Neither lane is the slider's path; recorded so nobody reads the script's `ok` as green.
- **Suites:** `test_dashboard_writes.py` 5 passed on the clean tree, with the browser test running, not skipped. `pixi run test-engine` 2582 passed, 56 skipped (this iteration, engine untouched since). The full CLI suite was run this iteration on the tree with ADR-504 on top of ADR-503; its result is in the next record, `orun2 D2: a design turn from the browser`.
- **D2 now:** item 2 (slider) has a browser test against a real engine with p50/p95 beside the raw bar; the write guard (127.0.0.1, per-launch token, same-origin) holds for every POST. Items 1, 3–6 remain.

Dispatch closed: 1 unit — backfilled record for ADR-503's slider write (commit 6eaeedeb) with measured slider p50 582/p95 636 ms beside the raw set_params bar (0.381 s; 0.482 s with display; bar 0.65 s).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 6eaeedeb4c22e470b750013d5dec509f621e2148

## State Impact

- target: twilight-aspen-1541 — item 2 (slider) evidenced: POST api/params runs cadex params as a child (one write path, A3) behind a per-launch token and Origin check on 127.0.0.1; headless-Chromium test against a real engine, release-to-drawn p50 582 ms / p95 636 ms (n=5) beside raw set_params 0.381 s (0.482 s with display, bar 0.65 s); items 1, 3-6 open
