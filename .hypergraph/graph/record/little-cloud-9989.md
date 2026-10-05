---
node_id: 2dc66eb4-f1e8-5a06-8fc1-941f752b43f8
slug: little-cloud-9989
title: 'P1 API contract: every GET /api route and its keys in docs/CLI.md, router dispatches from the table, test-pinned; browser keeps four convenience keys (ADR-552)'
created_at: '2026-10-05T14:33:01+00:00'
parents:
- sunny-oak-9772
summary: ''
---
## What

P1's second unit: the dashboard's HTTP API is a documented, test-pinned contract (ADR-552, commit `466f1dcd`). The browser-only-state audit is in the same unit.

## Why

The critic asked for this unit next: a table in `docs/CLI.md` of every `GET /api/...` route and its top-level keys, `activity` included; a test that enumerates the routes `ReviewHandler` really serves and fails when the table, a route or a key drifts, in the `OP_ARG_SPECS`/INTEGRATION.md style; and the browser-only-state audit as a short finding in the same record. This is P1's last open bullet set. Done as asked.

## Method

- `ReviewHandler._route` was a chain of `if rest == [...]` branches, so the only way to enumerate the routes was to read the source. It now resolves `api/` paths only through `review_server.API_ROUTES` (nine project routes) and `APP_API_ROUTES` (`projects`), using `match_api_route`. Each route has one `_api_<name>` method. Replies, status codes and URLs are unchanged, and anything not in the table gets the same 404 as before.
- `API_RESPONSE_KEYS` gives each route the keys every 200 reply carries and the keys only some replies carry. The `docs/CLI.md` section "The HTTP API (ADR-552)" has the same table.
- I seeded the key table by reading the source. Then I checked it with a key spy (a pytest plugin outside the repo that wraps `_send_json`) across a full `cli/tests` run: 222 `200` `/api` replies over eight routes. The spy found one key I had missed: a run with no rollout yet at the accepted revision borrows the accepted model, including its `meshes`. That key is now in the table, the doc and the fixture.
- `cli/tests/test_http_api.py` checks four things:
  1. The doc table equals `API_ROUTES ∪ APP_API_ROUTES` and, row by row, `API_RESPONSE_KEYS`.
  2. There is one `_api_` method per route and no other, and the only router lines that mention `"api"` go through `match_api_route`.
  3. A fixture biped reaches every route in each of its shapes: accepted model; walk training with a ready and a failed checkpoint; a run with a timed rollout, one without, and one symlinked out of the project; a borrowing run; a revision trail with an unretained first revision; an evaluation. It is served by `cadex review` and `cadex app`. Every reply carries its always-keys and nothing outside the table. Every promised key is seen at least once, except `video_render`, which needs a video status. Unknown `api/` paths return 404 with `{error, what}`.
  4. The page's scripts store only the four per-viewer `localStorage` keys and use no other browser storage.
- Mutation check: three changes each fail the test. They are an extra `/api/project` key, a deleted doc row, and a fifth `localStorage` key.

## Result

What is true now:
- Every `GET /api/...` route and its top-level keys are listed in `docs/CLI.md` "The HTTP API (ADR-552)". The router dispatches from the same table, and a test fails if the doc, the tables or the live replies disagree.
- **Browser-only-state audit (finding).** The page keeps no project state in the browser. `localStorage` holds four per-viewer conveniences: `cadex.theme`, `cadex.layout.v3`, `cadex.render` and `cadex.overlay`. There is no sessionStorage, IndexedDB or cookie. A picked checkpoint, a scrubbed revision or a selected run lasts only as long as the page. The projects index keeps its page number in the URL query, not in storage. The doc names the four keys, and the test pins them.
- With ADR-551 (relative URLs, prefix proxy test) and this unit, every P1 bullet has evidence. P1 is ready to move to working at the next reconcile.

Gates:
- `pixi run test-engine`: 2585 passed, 58 skipped.
- `pixi run python -m pytest cli/tests` with the GPU hidden: 1162 passed, 1 skipped. The skip is the `CADEX_REVIEW_HOST` private-network test, which is environmental. That run used the final router. After it, only the key table (one added optional key), the docs and the new test changed. I re-ran `test_http_api.py` and `test_project_docs.py` (33 passed), and the review, app, prefix, checkpoint, revision, evaluation and read-only suites (92 passed, 1 skipped).
- No protocol or payload change, so the packaged gate does not apply.

Concerns:
- Non-`api/` file routes (`mesh/…`, `artifact/…`, `video/…` and the rest) are outside the table by design. They are served only when a reply offers them.
- A `run/<run>` reply passes through whatever `run.json` holds. Its optional keys are pinned to what `write_run_record` writes, which the fixture's walks exercise.

The unreconciled tail is now two records (sunny-oak-9772 and this one). The critic asked for a reconcile after this unit so P1 can move to working.

Dispatch closed: 1 unit — the dashboard's HTTP API is a route table the router dispatches from, listed in docs/CLI.md and pinned by test_http_api.py, plus the browser-state audit (ADR-552)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: 466f1dcd4c8a5af3e67b18cbadaf495ae064162b

## State Impact

- target: still-spring-3327 — P1's second unit landed (ADR-552, commit 466f1dcd): every GET /api route and its top-level keys are listed in docs/CLI.md 'The HTTP API'; ReviewHandler dispatches only from review_server.API_ROUTES/APP_API_ROUTES; API_RESPONSE_KEYS holds the keys; test_http_api.py holds doc, tables and a fixture biped's live replies together. Browser audit: only cadex.theme, cadex.layout.v3, cadex.render, cadex.overlay in localStorage, test-pinned. With ADR-551 every P1 bullet has evidence; ready for working.
