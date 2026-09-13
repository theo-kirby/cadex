---
node_id: fb840f7c-159a-58ab-bc06-750340908421
slug: royal-road-2298
title: Review page follows its design spec at 1400 and 400x850 (ADR-329); retroactive record for 9a4ff012
created_at: '2026-09-13T21:54:46+00:00'
parents:
- ancient-field-7584
summary: ''
artifacts:
- cli/cadex_cli/review_static/review.css
- docs/review-design/after-400x850.png
- docs/probes/ot6/design/after.json
---
## What

The retroactive record for commit `9a4ff012` ("ouroboros #3: no record"), the iteration that applied `docs/REVIEW-DESIGN.md` to the page and committed without a record node. It changed `cli/cadex_cli/review_static/{index.html,review.css,review.js}` to the spec (ADR-329): one dark greyscale palette on `:root` whose `--bg` is the environment module's dark scene background; one type scale (12/14/17/22 px); six regions in the charter's reading order under numbered sentence-case headings; the videos in a region of their own; training, parameters, artifacts and documents as the record appendix; the run list a sticky 280 px sidebar at desk and a closed `<details>` disclosure below 600 px, folded by the media query alone; a stat row over an `auto-fit` history grid; every table scrolling inside its card; the fixed 520 px canvas replaced by a 16:9 box (4:3 on phone) with `touch-action: none`. No element id or `data-*` hook changed. Beside it: the after screenshots and receipt (`docs/review-design/after-1400.png`, `after-400x850.png`, `docs/probes/ot6/design/after.json`, captured by the renamed `capture_page.py`), §8 of the spec, ADR-329, a `docs/CLI.md` pointer, and the rendered-page half of `cli/tests/test_review_design.py`.

## Why

Ladder rungs 1 and 2 for D1 (`floral-marsh-2830`) and the layout half of D2 (`western-journey-2108`), following the spec unit `ancient-field-7584`. The record was not written in that iteration; the critic asked for it first, with verified evidence and the remaining gaps, and this is it — written by the next iteration, from the commit and by re-running its tests, not from memory.

## Method

Verified on 2026-09-13 by iteration 4: `git show --stat 9a4ff012` (11 files, 631 insertions, 118 deletions); `pixi run python -m pytest cli/tests/test_review_design.py -q` on that commit: **17 passed in 2.42 s** with a Chromium present, so the rendered-page tests ran rather than skipped; `docs/probes/ot6/design/after.json` read against §8 of the spec; `review_scene.js` read for its input handlers; the operator service checked (`cadex-operator-review` user unit active, serving `ot5-lark-copy85` on port 8765, the address read from the unit and never committed).

## Result

What is true now, verified:

- The page follows §2–§6 of the spec at both charter sizes, on the fixture project (the design test) and on the operator URL (the receipt): layout viewport 1400 / **400** px, horizontal overflow 0 / **0**, canvas 999×562 / **350×263**, page height 3 829 / 6 463 px, type 14/22/17/12, every palette token computed to the spec's value, headings `1 Runs` … `6 Record` in sentence case, the disclosure closed on the phone and opening on a click.
- The receipt was captured on `ot5-lark-copy85` with `lark109-engine2` selected, live, model loaded — the operator URL serves the active project and run in the new design.

The gaps, which the commit's §9 overstated and the critic named:

- **Touch orbit is not implemented, let alone tested.** `review_scene.js` registers `mousedown`/`mousemove`/`mouseup`/`wheel` only; with `touch-action: none` on the canvas a finger drag on a phone neither scrolls nor orbits. §9's "a touch orbit that changes the camera" describes no test in the suite.
- **No phone playback or download test.** The design test's phone half asserts layout only (viewport width, overflow, tokens, type, canvas width, disclosure, stacked curves). §9's "a video that plays and downloads" on the phone is not in the suite; the ot5 playback and download tests run at the default desk size.
- **No per-region phone screenshots.** One full-page phone screenshot exists (`after-400x850.png`); the charter asks for each region at 400 × 850.
- **The viewport still renders the light scene** (`review_scene.js` `STYLE = 'cadex-prototype-light-v1'`, environment `light` palette), so D1's "one palette across chrome and viewport" holds for the chrome only until D3.

No engine, protocol, payload, shell or dependency change. The full CLI suite was not run in that iteration; iteration 4 runs it.

Dispatch closed: 1 unit — the review page brought to its design spec at 1400 and 400×850 (ADR-329), after screenshots and receipt on the operator URL, rendered-page design test; touch orbit, phone playback/download and per-region screenshots still open.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: 9a4ff0125e0f9af91777db5222c274c0d7eedfcd

## State Impact

- target: floral-marsh-2830 — D1's page half exists: the chrome follows REVIEW-DESIGN.md §2–§6 at both charter sizes with after screenshots, receipt and the rendered-page design test (tokens, type, overflow, canvas fill) on the operator URL; the viewport still renders the light scene until D3
- target: western-journey-2108 — D2's layout half exists: at 400×850 the layout viewport is the device width with no overflow, the run list is a closed disclosure, the canvas fills the width, curves stack; touch orbit is not implemented (mouse-only handlers), and phone playback, download and per-region screenshots are untested
