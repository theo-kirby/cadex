---
node_id: b77bcabf-ce35-5958-88cf-ab283aec8d6e
slug: cold-mist-9459
title: 'D3: one-click layout presets, empty areas and a labelled drop preview (ADR-573)'
created_at: '2026-10-06T20:49:44+00:00'
parents:
- neat-isle-1523
summary: ''
---
## What

D3: layouts come from one-click presets, an area may be empty, and an area drag previews where it lands (ADR-573). `layout.js` gains `preset(name)` over eight shapes (single, side, stacked, two_over_one, one_over_two, columns, rows, quad): equal shares, filled in reading order with 3D viewport, Status, 2D viewport, the rest `empty`. View → Layout shows eight icon buttons (`#layout-presets button[data-preset]`) under Reset; one click applies a preset and closes the menu. An `empty` pseudo-editor (any number of times) has the editor picker and a hint line; picking an editor there moves it in. `show(type)` fills an empty area before splitting. The grip is more visible (80 % → 100 % on hover, grab cursor) and the drop preview names its landing: Swap / Dock left / right / above / below.

## Why

The critic named D3 as the next unit (last page criterion before C1). Done as asked. For quad's fourth area the critic's rule was: a second 2D viewport if the layout can show an editor twice cheaply, else an empty area with the picker. It cannot — an area moves its editor's own DOM so a canvas keeps its WebGL context (ADR-534); a second 2D viewport would need a second sheet stage in `review.js` — so quad's fourth area is empty, and ADR-573 records the choice and how to undo it.

## Method

Edited `cli/cadex_cli/review_static/{layout.js,index.html,review.js,review.css}`; `docs/DASHBOARD.md` §2 and §12 and ADR-573 in the same commit. New Chromium test `cli/tests/test_review_layout.py` through `cli/cadex_cli/browser.py`: applies all eight presets through the View menu by click and checks editors and geometry of each area against the shape (±2.5 % of the screen per side), picker on every area, menu closed, tree kept in `cadex.layout.v4`; quad's empty area shows the picker and line, picking the 2D viewport moves it in, layout survives a reload; on side by side, drags the 3D viewport's grip to Status's right edge, asserts the preview covers that half and reads "Dock right", and the drop puts Status first; Reset restores the default tree. Fails without the change (no `#layout-presets`, no `preset`). Visual check of quad and the menu at 1280×900 (not committed).

## Result

D3 has evidence: area counts per preset measured 1, 2, 2, 3, 3, 3, 3, 4. `test_review_layout.py` + `test_review_status.py`: 18 passed in 27.9 s. Gates: `pixi run test-engine` 2611 passed, 58 skipped (5:46); CLI suite in three foreground-equivalent thirds with the GPU hidden: 392 passed (2:31), 324 passed 1 skipped (5:45), 488 passed (3:53) — green. (The first third ran in the background by mistake and was awaited with a monitor before the turn went on.)

C1 still needs one PNG screenshot per preset (≤300 KB, dark floor) under `docs/probes/orun4/`; `window.cadexReview.layout().preset(name)` makes them scriptable. No route, API key, localStorage key, engine module, protocol op or tool schema changed; no new dependency. Tail is two unreconciled records with this one.

Dispatch closed: 1 unit — D3 layout presets, empty areas, labelled drop preview (ADR-573)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 70304ce68d7998307eecd014156e0f897fbf094f

## State Impact

- target: southern-pond-2017 — D3 has evidence: eight presets in View → Layout, each applied by one click and measured in Chromium (1,2,2,3,3,3,3,4 areas), quad's fourth area empty with its picker, a labelled drop preview and a stronger grip, Reset restores the default (ADR-573, test_review_layout.py)
