---
node_id: ceadfe77-12b9-5a46-b79b-172f5590820a
slug: copper-union-7670
title: Viewer floor grid anchored to world origin; no slide on zoom (ADR-343)
created_at: '2026-09-14T16:34:18+00:00'
parents:
- bold-river-6496
summary: ''
---
## What

The viewer's floor grid is now anchored to the world origin (ADR-343). Before, zooming slid the grid under the model, so the "1 METER" squares did not sit where a metre is.

## Why

The owner reported the floor doing "a weird tiling thing" on zoom. A 1 m grid box has to stay 1 m in real size and in a fixed place.

## Method

**Probe.** A headless Chromium on the operator dashboard (ot6-heron) scaled the fit distance by k, then read `viewer.stats().stage`.
- The floor stayed 24 m for k ≤ 1.3.
- Beyond that it grew: 25.025 m at k = 2, 50.05 m at k = 4.
- The texture was tiled from the plane's corner, so the phase of world x = 0 inside a 2 m block went 0 → 0.256 → 0.512.

**Fix.**
- `floor.js`: builds a unit plane scaled to the footprint. The texture offset is `-(size/2)/(2·pitch)` mod 1, set by the new `resizeStageFloor`.
- `environment.setSize`: repaints only when pitch or minor changes.

**Check.** A top-down camera aimed at world (3 m, 3 m) at 1.5, 3, 6 and 12 m showed a major-line crossing at the frame centre every time.

**Regression test.** `test_floor_grid_is_anchored_to_the_world_whatever_the_floor_size` covers sizes 24, 25.025, 50.05, 84 and 671.3 m.

## Result

`test_video`, `test_review_style_evidence`, `test_review_design` and `test_review_server` gave 216 passed, 1 skipped. The new test passes. The minor mesh still steps with framing (ADR-331), by design.

Not done: I did not run the new test against the old code. The old `floor.js` has no `resizeStageFloor`, so the test would throw rather than show the slide. The slide itself is evidenced by the probe numbers above.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: eee7041c4b67eb28b12f8d949d97f56b3a49d5c1

## State Impact

- target: fair-wolf-4645 — the viewport mat's major grid lines are world-anchored (ADR-343); before, zooming past a 24 m floor slid them by up to half a 2 m block
