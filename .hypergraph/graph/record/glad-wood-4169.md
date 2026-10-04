---
node_id: 8aa78c75-a58f-573a-ba60-8a711c3068e7
slug: glad-wood-4169
title: 'Dashboard cut to the minimum: model, turn, sliders, revisions; paginated index (ADR-533)'
created_at: '2026-10-04T11:50:20+00:00'
parents:
- grand-spring-8971
summary: ''
---
## What
The dashboard's three pages were cut to the minimum (ADR-533, owner direction 2026-10-04), keeping their structure. The project page now has only the model, a design turn (prompt / continue / start, plus a transcript), the parameter sliders and the revision list (accept / reject / restore). The index lists projects newest first, 20 to a page (`?page=N`), with runs above them. A run's page shows its charter criteria (ticked or not) and its iterations with the critic's verdict and reason.

## Why
The owner asked for "the simplest possible version, and then we can add stuff back as needed". The HTTP API was left unchanged, so bringing back any removed panel is work on the page only.

## Method
- Rewrote `review_static/` index.html, review.js, review.css, projects.*, run.* and viewer.js. Deleted markdown.js and dimensions.js.
- Rewrote DASHBOARD.md down to the surviving sections, keeping their numbers. Updated CLI.md and added a note to SHELL-PARITY.md.
- Deleted the browser tests for removed panels and rewrote the tests for what stays. Added `test_app.py::test_browser_pages_through_the_projects_newest_first`. Receipt tests that cite deleted tests get the `REMOVED_BY_ADR_533` allowance.
- Checked by screenshot in headless Chromium at desk (1440) and phone widths, and through the `/cadex` tailscale proxy.
- Operator-side fix: `~/cadex-dash/proxy.py` no longer rewrites quoted paths in JS. That rewrite had doubled the prefix together with the page's BASE (`/cadex/p/x/cadex/api/project`), so clicking a project never loaded its model.

## Result
- `review_static` plus the server: −3,055 / +334 lines. review.js went from 1,975 to 355 lines.
- `cli/tests`: −3,348 / +191 lines.
- DASHBOARD.md went from 1,274 to 646 lines.
- `pixi run python -m pytest cli/tests` (GPU hidden): 1360 passed, 1 skipped.
- Served at https://sb1x.tailf21f57.ts.net/cadex/ from branch dashboard-minimal, commit 904f3f98.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: dashboard-minimal
- commit: 904f3f98fc4fc98fac3ab606f808508af0f3f634

## State Impact

- target: twilight-aspen-1541 — still true on a cut page: from a browser a person sees the model, runs a turn, drags sliders and accepts/rejects/restores revisions; the inspect/parts/dimensions/export/comment/render panels are removed from the page by ADR-533 (API kept, CLI equivalents kept)
- target: swift-nest-0229 — run page reduced to charter criteria + iterations with critic verdict/reason (ADR-533); index paginates projects newest first, 20 per page
