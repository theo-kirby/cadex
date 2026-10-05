---
node_id: 672d6e49-5428-578c-9ae5-5572c85aa205
slug: sunny-oak-9772
title: 'P1 URL cut: every dashboard URL relative to the page, works under /some/prefix/ (ADR-551)'
created_at: '2026-10-05T14:08:00+00:00'
parents:
- early-crow-5889
summary: ''
---
## What
P1's first unit, the URL cut (ADR-551, commit `ea1a00e4`). Every URL the dashboard fetches or links, and every URL the server builds into a response, is now relative to the page. The dashboard works unchanged behind a path-prefix proxy that rewrites nothing.

## Why
The critic named P1 as the next unit and asked for the URL cut first: `review.js`'s root-absolute literals, `projects.js`, and the URLs `review_server.py` builds. Then a test serving the dashboard under `/some/prefix/` through a non-rewriting proxy and loading a biped project in the browser, an ADR, DASHBOARD.md and CLI.md. Done as asked. The route-and-key contract test is left to P1's second unit, as the critic said.

## Method
- Server (`review_server.py`, `revision_meshes.py`):
  - `mesh` is now `mesh/accepted|run|revision/...`;
  - playback `url` is `api/playback/...`;
  - `/api/projects` `url` is `p/<name>/`;
  - the `p/<name>` → `p/<name>/` redirect `Location` is `<name>/`.
  These were all 12 root-absolute builds. The other URLs (`presentation/`, `export/`, `blueprint/`, `doc/`, `evaluation/`) were already relative.
- `review.js`:
  - `BASE` is removed. All fetches are relative (`api/project`, `api/model/...`, `api/run/...`), and manifest URLs are used as given.
  - App mode against review mode is now `NAME`, taken from `/p/<name>/(index.html)?$` anywhere in the pathname, so a prefix does not change it.
  - `projects.js` already fetched `api/projects` relatively. Its links now follow the server's relative `url`.
- `index.html` and `projects.html` declare `<link rel="icon" href="data:,">`. Before that, the browser's own `/favicon.ico` probe was the one stray request outside the prefix.
- New `cli/tests/test_dashboard_prefix.py`, with a standard-library proxy that forwards `/some/prefix/<rest>` to `/<rest>` with body and headers unchanged, and records any request outside the prefix:
  - (a) no `url` or `mesh` in `/api/projects`, `/api/project`, `/api/model/accepted` or each run's `/api/model/run/<name>` starts with `/`, and the redirect `Location` is `biped/`;
  - (b) in Chromium, the app index → the bare `p/biped` redirect stays inside the prefix → the biped model draws, the File menu lists both projects, and Home is `/some/prefix/`, with zero strays;
  - (c) a `cadex review` page under the prefix draws the model with Home hidden and zero strays.
- Five existing tests that pinned the absolute forms now pin the relative ones.
- Docs:
  - DASHBOARD.md §2 project line and §22 (replacing "a sub-path mount is not tested");
  - CLI.md: the `cadex app` row, the `/mesh/revision` paragraph and a test-table row;
  - DECISIONS.md: ADR-551.

## Result
- The dashboard is portable under a path prefix. The fixture is the biped `_review_project` in both the app and review modes.
- Before and after, measured: with the source changes stashed, all 3 new tests fail (URLs start with `/`, the index link leaves the prefix, the review page's poll leaves it). With the change, all 3 pass.
- Gates, run with the GPU hidden (`CUDA_VISIBLE_DEVICES=`):
  - `pixi run test-engine`: 2585 passed, 58 skipped;
  - `pixi run python -m pytest cli/tests`: 1162 passed, 1 skipped. The engine is built, so the engine-needing half ran.
- No protocol or payload change, so the packaged gate was not needed.
- P1's remaining items:
  - (1) the HTTP API contract: every `GET /api/...` route and its top-level keys in `docs/CLI.md`, or one file it points to, pinned by a test like the `OP_ARG_SPECS` one, with `activity` included;
  - (2) the "no page state only in the browser" audit, which has no change here.
- Assumption: app mode is detected from the page's own path ending in `/p/<name>/`. A `cadex review` mounted under a prefix that itself ends in `/p/<x>/` would be misread as app mode. That is unlikely, and it is noted in the ADR's design.
- Tail is now 1 unreconciled record.

Dispatch closed: 1 unit — P1 URL cut: all dashboard URLs relative, proven through a non-rewriting /some/prefix/ proxy (ADR-551)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: ea1a00e409b5bf9765f364ef2f6aa08241c00595

## State Impact

- target: still-spring-3327 — URL half met: every page fetch/link and server-built url/mesh/redirect is relative (ADR-551, ea1a00e4); test_dashboard_prefix.py loads a biped project in Chromium through a non-rewriting /some/prefix/ proxy with zero stray requests. Remaining: the GET /api route+key contract test (with activity) and the browser-only-state audit.
