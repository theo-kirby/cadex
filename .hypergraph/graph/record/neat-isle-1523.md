---
node_id: 90ba8a71-e548-54fc-a1ef-61c3ea6c415a
slug: neat-isle-1523
title: 'D2: Status is its own editor beside the 3D viewport (ADR-572)'
created_at: '2026-10-06T20:28:06+00:00'
parents:
- frosty-cabin-1461
summary: ''
---
## What

orun4 D2: the stage overlay (ADR-542) is now an editor of its own, `data-editor="status"`, shown as **Status** (ADR-572). It sits beside the 3D viewport in the default desk layout and is a tab on a phone. It can be put in any area, docked and swapped like the 3D and 2D viewports. The 3D viewport keeps the checkpoint scrubber, the revision timeline, playback and the model-status line.

## Why

The critic's message named D2 as the next unit, after H2 and H3 were reconciled. D2 is the highest-ranked open criterion in the charter's order (F1, F2, G1, G2 and H1–H3 have evidence; D1 is working). I did what the message asked.

## Method

- `index.html`: a new `#editor-status` section in the editor shelf. Its tool is the stage chip `#status-stage[data-stage]`, which goes in the area header. Its body `#status[data-stage]` holds the line, run, activity, stats, sparklines and warning. Every `#overlay-*` hook is renamed to `#status-*` and keeps its content.
- `review.js`: `ORDER = ['view3d', 'status', 'view2d']`. `DEFAULT_LAYOUT` is a row split, 3D at 0.75 and Status at 0.25. The layout key moves to `cadex.layout.v4`, so a browser holding a v3 layout gets Status instead of hiding it. `renderOverlay` becomes `renderStatus`. The collapse toggle, `setOverlayCollapsed` and the `cadex.overlay` key are removed: an area is sized by its edges and a phone uses tabs, so collapsing no longer has a job.
- `review.css`: the overlay's absolute box becomes a scrolling editor body, and the chip colours key off the chip's own `data-stage`.
- Tests:
  - `test_review_overlay.py` is renamed (`git mv`) to `test_review_status.py`, and every test is kept on the renamed hooks.
  - Its collapse and quarter-of-the-viewport-at-390-px test is replaced by `test_status_is_an_area_at_a_desk_a_tab_on_a_phone_and_docks_like_the_others`, which drives Chromium through `cli/cadex_cli/browser.py`. It checks the default desk layout `[view3d, status]`: Status to the right, the same height, less than half the 3D width, the chip in its header, nothing of Status inside `#model`, and all three timelines still in it. It then drags Status's grip onto the middle of the 3D viewport, asserts the two areas swap, and checks that Reset restores the default. At 390 px it checks the tabs `3D`, `Status`, `2D`; that the 3D tab has no status; and that the Status tab is 390 px wide with the training stage and warning and no horizontal overflow.
  - `test_review_checkpoints.py` drops its "below the overlay" assertions.
  - `test_review_design.py` pins the Status hooks, the two-area default and three tabs.
  - `test_http_api.py` pins the three `localStorage` keys.
- Docs:
  - `docs/DASHBOARD.md`: the §2 row becomes **Status** / `status`, and §1, §6 and §12 are updated (default layout, tabs, `cadex.layout.v4`).
  - `docs/CLI.md`: the poll paragraph and "What the browser keeps" (three keys).
  - `review_server.py`: comments only.
  - ADR-572 is added to `docs/DECISIONS.md`.

## Result

Status is an editor. Measured in Chromium:
- At 1400 × 900, Status is 317 × 769 px beside a 951 × 769 px 3D viewport.
- At 390 × 844, the Status tab is 390 × 756 px.
- A desk screenshot (not committed) shows the chip in the area header, and the numbers and sparklines in the Status body, with nothing over the model.

Targeted suites: `test_review_status.py`, `test_review_design.py`, `test_http_api.py` and `test_review_checkpoints.py` gave 163 passed.

Gates, with the GPU hidden:
- CLI suite, in the charter's three thirds: 425 passed and 1 skipped (NR%3==0); 365 passed (NR%3==1); 413 passed (NR%3==2). In total that is 1203 passed and 1 skipped.
- `pixi run test-engine`: 2611 passed, 58 skipped.

No file under `src/Mod/cadex` changed, so no engine build or stage was needed.

No route, API key, engine module, protocol op or tool schema changed.

Concerns for the next iteration:
- D3 builds on this. There are now three editors, so presets like quad or three rows must decide what fills a fourth area. Each editor shows at most once in `layout.js`, so a quad needs either a fourth editor or a rule that allows repeats. Decide that in D3's ADR.
- The known flake in `test_designing_turns_idle_once_the_window_passes` (minute boundary) is in the renamed file and was left alone.

Dispatch closed: 1 unit — D2: Status is its own editor beside the 3D viewport, a tab on a phone (ADR-572)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: adb94bb138fcdda85ac3206c60feed6ff140e193

## State Impact

- target: staid-slope-4052 — D2 met: the stage overlay is the Status editor (data-editor=status), an area right of the 3D viewport by default at a desk and a tab on a phone, dockable and swappable; collapse and cadex.overlay removed; scrubbers stay in the 3D viewport; Chromium test through browser.py; suites green (ADR-572)
