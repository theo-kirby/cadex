---
node_id: a483246e-853f-5bc0-bc77-97c90b3dd856
slug: bold-river-6496
title: 'Review dashboard desk frame: resizable sidebars around a tabbed stage (ADR-342)'
created_at: '2026-09-14T16:10:22+00:00'
parents:
- nimble-wing-3050
summary: ''
---
## What

The review dashboard's desk layout (≥ 1000 px) became an application frame at the owner's direction (ADR-342). There is a 44 px top bar. Left and right sidebars share the bar's surface and meet it at the stage's rounded corner. Each sidebar's inner edge drags to resize the sidebar or fold it away. The centre is a tabbed stage: Model by default, then Curves, Videos, and a Document tab while a document is open. Information, settings and parameters moved into the sidebars by type.

## Why

The owner asked for it directly. The model should always be the centre. Other centre content (videos, plots, future modules) goes on the stage. Every descriptive module goes in a sidebar. ADR-341 had left the dashboard to the owner's own work (`nimble-wing-3050`).

## Method

- `cli/cadex_cli/review_static/index.html`: restructured into `#top`, `#left`, `#stage` (tabs plus panels) and `#right`. Every pinned id is kept.
- `review.css`: rewritten narrow-first. Below 1000 px the frame containers are `display: contents` and use `order`, so phone and tablet read in the §2 order as before.
- `review.js`: a second closure handles pointer drags on the handles, fold on release under 120 px, the top-bar toggles, keyboard arrows and Enter, foldable sections, stage tabs (via MutationObservers on `#doc-view`, `#telemetry` and `#videos`), a ResizeObserver redraw on the canvas, and layout persistence in localStorage.
- No server change and no new static file.
- Spec: `docs/REVIEW-DESIGN.md` §12, plus edits to §2, §3, §5 and §6. `docs/CLI.md` updated.
- Tests: `test_rendered_page_follows_the_spec[desk]` was rewritten for the frame geometry. The new test `test_desk_sidebars_drag_fold_and_the_stage_changes_what_it_shows` drives it with a real mouse.

## Result

- **Visual check.** Screenshots of the live operator dashboard (ot6-heron) at 1400×900, 1000×800 and 400×850. At desk the page shows three columns with no page scroll. The phone layout is unchanged.
- **Tests.** `pixi run python -m pytest cli/tests` gave 615 passed, 2 failed and 1 skipped on the first full run. Both failures are fixed, and both tests pass on re-run:
  - `test_browser_orbit_and_zoom…`: Fit is now aspect-aware for portrait canvases, so the test takes its reference Fit at the size it measures.
  - `test_arriving_disk_detail…`: a race already in the test, between its 15 s held request and its 15 s wait, which the new layout tipped. The wait now outlasts the hold.
- **Proxy test.** It folds both sidebars, because its 3–5× proxies need a wide stage.
- **Fit.** It now frames by the narrower field of view. Output is unchanged for aspect ≥ 1, so captures are unaffected.
- **Not re-run.** The full suite was not re-run after those three test edits. Only the affected tests were run again.
- **Dead end.** A sidebar drag used to jump the edge by half the handle width, and a drag-to-fold remembered its last intermediate width. Both were fixed: the handle keeps the grab offset, and a fold keeps the width from before the drag.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: eee7041c4b67eb28b12f8d949d97f56b3a49d5c1

## State Impact

- target: floral-marsh-2830 — D1's desk layout superseded by the frame of REVIEW-DESIGN.md §12 (ADR-342): thin top bar, two drag-resizable/foldable sidebars organised by type, stage with Model/Curves/Videos/Document tabs; phone layout (D2) unchanged; awaiting owner review
