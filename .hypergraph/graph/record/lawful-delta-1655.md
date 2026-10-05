---
node_id: 347d6897-a036-5bca-821c-f56e1a0d930d
slug: lawful-delta-1655
title: Model status line reads on the dark floor, below the overlay, at 390 px in both themes (ADR-557)
created_at: '2026-10-05T17:20:01+00:00'
parents:
- careful-lantern-1462
summary: ''
---
## What
ADR-557, commit `e49f0394`. `#model-status` says why no model is drawn. It moved from a transparent line at the 3D viewport's top left to the first item of the viewport's bottom column (`.timelines`), above the scrubbers. It now sizes to its text, wraps, and has an opaque `--surface` behind it. This closes the light-theme gap that REPORT §5 named after ADR-556.

## Why
The critic named this as the next unit. At 390 px in the light theme, `--warn` (#8a6100) sat on the dark viewport floor, and the line was partly under the expanded overlay. The critic asked for readable contrast, the line kept below the overlay, and both pinned in the same phone test. The critic's fix-first was the ADR-556 record, which is done as `careful-lantern-1462`. The critic also asked for a reconcile, and that was **not** done: this dispatch forbids the hypergraph-reconcile skill in a work iteration, with no exceptions. "Below the overlay" is read as *vertically below and never covered by it*, which is stricter than stacking order. That is the most reversible reading.

## Method
The test was written first: `test_the_model_status_line_reads_on_the_dark_floor_below_the_overlay_at_390px` in `cli/tests/test_review_checkpoints.py`, run in the light and dark themes. Chromium was driven through `browser.py` at 390 × 844 with touch emulation and the overlay expanded, on a biped revision whose model was not kept (`missing`). It checks these things:
- the line is inside the viewport and not clipped;
- its top is ≥ the overlay's bottom;
- its colour is the theme's `--warn`;
- its background is opaque, with a WCAG contrast of ≥ 4.5:1.

Before the change, the test failed: the line's top was at 84 px and the overlay's bottom at 149 px. On the #141414 floor (`environment.js`), the light theme's `--warn` is about 3.3:1. The fix is one markup move in `index.html` and one CSS rule. No script, route or key changed. The `docs/DASHBOARD.md` 3D-viewport row, the ADR, and REPORT §4 and §5 changed in the same commit.

## Result
- Light theme: 5.04:1. Dark theme: 13.35:1. The line's top is 457 px below the expanded overlay in both themes.
- ADR-556's scrubber test still measures 287 px and 303 px.
- `pixi run python -m pytest cli/tests` with the GPU hidden: 1178 passed, 1 skipped.
- `pixi run test-engine`: 2585 passed, 58 skipped.
- The protocol and payload were not touched.
- At desk width the line now sits at the bottom left rather than the top left. That is a visible change, recorded in the ADR.

Concern: the unreconciled tail is now four records: easy-grove-4224, empty-jasper-3681, careful-lantern-1462 and this one. That is over the charter's three-record threshold, so the next iteration should be the reconcile, followed by a renewed done claim. The remaining long-term rung is binary meshes, which have not been started.

Dispatch closed: 1 unit — model status line readable on the dark floor and below the overlay at 390 px (ADR-557)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: e49f039473d4e46222f8854ade4119e954780844

## State Impact

- target: vast-ivy-6277 — #model-status heads the viewport's bottom column on an opaque --surface: 5.04:1 light, 13.35:1 dark, below the expanded overlay at 390 px (ADR-557, e49f0394); REPORT §5 light-theme gap closed
