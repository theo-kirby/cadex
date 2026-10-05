---
node_id: c23b6445-8a7b-5d24-bf40-737efb9e541c
slug: still-spring-3327
title: P1. The dashboard is portable
created_at: '2026-10-05T08:57:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

orun3 charter criterion: **P1. The dashboard is portable.** Every bullet now has measured evidence; the owner ticks the charter box. [rec: golden-snow-6627] [rec: little-cloud-9989]

- **Relative URLs, proven under a prefix (met).** Every page fetch and link, and every server-built url/mesh/redirect, is relative to the page (ADR-551, `ea1a00e4`). `test_dashboard_prefix.py` loads a biped project in Chromium, in both app and review modes, through a non-rewriting `/some/prefix/` proxy with zero stray requests; the 3 tests fail with the change stashed. Known misread: a `cadex review` mounted under a prefix that itself ends in `/p/<x>/` is read as app mode (named in ADR-551). [rec: sunny-oak-9772]
- **The HTTP API is a pinned contract (met).** `ReviewHandler` dispatches `api/` only from `review_server.API_ROUTES` (nine project routes) and `APP_API_ROUTES` (`projects`); `API_RESPONSE_KEYS` holds each route's always/sometimes keys; `docs/CLI.md` "The HTTP API (ADR-552)" lists the same table. `cli/tests/test_http_api.py` holds doc, tables and a fixture biped's live replies together (every shape, both servers, 404 for unknown `api/`), and fails on an extra key, a deleted doc row or a fifth `localStorage` key (`466f1dcd`). File routes (`mesh/…`, `artifact/…`, `video/…`) are outside the table by design. [rec: little-cloud-9989]
- **No project state only in the browser (met).** `localStorage` holds only four per-viewer keys — `cadex.theme`, `cadex.layout.v3`, `cadex.render`, `cadex.overlay` — test-pinned; no sessionStorage, IndexedDB or cookie; the projects index keeps its page in the URL query. [rec: little-cloud-9989]
- Gates at both units: `pixi run test-engine` 2585 passed, 58 skipped; `cli/tests` (GPU hidden, engine built) 1162 passed, 1 environmental skip. No protocol or payload change. [rec: sunny-oak-9772] [rec: little-cloud-9989]

Judgement (maintainer): status flipped open → working on little-cloud-9989's declared "every P1 bullet has evidence; ready for working", derivable from the two cited records' measured gates. [rec: little-cloud-9989]

## Negative knowledge

None yet.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-p1-dashboard-portable-no-page)
- sunny-oak-9772 — URL half: relative URLs, prefix-proxy browser test (ADR-551)
- little-cloud-9989 — API route/key contract test and browser-state audit (ADR-552); P1 to working
