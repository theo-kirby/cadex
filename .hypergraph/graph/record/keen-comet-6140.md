---
node_id: 56a41bef-1560-5de0-b6e6-4a26054820c6
slug: keen-comet-6140
title: 'ot10 A8: the dark prototype floor — one palette source for every presented image (ADR-444)'
created_at: '2026-09-29T07:24:26+00:00'
parents:
- snowy-quill-0006
summary: ''
---
## What

ot10 A8: every presented image now stands on the review viewport's dark prototype floor (ADR-444). A new module, `cli/cadex_cli/scene.py`, is the only palette source. It reads the scene background and the mat's tiles and major line from `PALETTE` in `review_static/environment.js`, and it reads `--ink`, `--ink-2` and `--rule` from `review_static/review.css`. These are the files the dashboard loads.

- **Floor.** `render.studio` draws the floor as that mat through `render._floor`: a checker one grid pitch square, with the major line on every pitch multiple anchored at the world origin. The pitch comes from `floor.js`'s ladder. Line coverage is computed from the pixel's floor footprint, so the grid is antialiased. The mat fades into `#141414` between 0.75× and 1.9× the framed extent. A level view draws only the background.
- **Contact shadow.** Deepened for the dark floor: the minimum is now 0.2 (was 0.45).
- **Concept sheet and SVG views.** The sheet's paper, ink and rules and the review SVGs' paper and caption now come from the scene.
- **Video identity.** `video.studio_digest` now also hashes `scene.py` and both palette files.
- **Removed.** The light `BACKDROP_*` gradient, the sheet's light colours and the SVG's `#f6f7fa` are deleted, not kept behind a switch.

This change covers the hero, the four review views, `look`, the concept sheet and the studio rollout video.

## Why

The critic named A8 as the next and last product unit. The owner's exhaustion policy puts A8 after the A7 unit in progress (ADR-443, landed) and before the close. I did what the critic asked:
- one palette source;
- hero, sheet, `look` and video drawn from it;
- a drift test;
- the shadow kept readable;
- before and after images of one A5 design and the W2 video, all under 300 KB;
- `docs/REVIEW-DESIGN.md` §16 and ADR-444;
- no re-scoring.

The engine and payload are untouched (the change is `cli/` only), so the packaged gate does not apply.

## Method

- **Palette.** `scene.py` parses the viewport's own files. Nothing else in the tree copies a scene colour, and a test asserts that for `render.py`, `sheet.py` and `video.py`.
- **`cli/tests/test_scene_palette.py`** (8 tests):
  - the renderer's palette equals the viewport's, parsed independently, and equals the charter's `#141414`/`#1c1c1c`/`#232323`/`#3a3a3a`;
  - `floor.js`'s fallback tile, pitch ladder and 5/256 line width match;
  - the sheet's chrome equals the page's tokens;
  - the hero stands on the mat, and a level view is plain background;
  - the mat fades with distance;
  - a changed viewport palette changes the drawn pixels;
  - an unreadable `PALETTE` refuses;
  - the video's identity covers the palette files.
- **Existing tests updated where they encoded the light look:**
  - `test_look.py`: hero backdrop, shadow ratio, the graphite classifier (the neutral dark floor is no longer counted as mechanism), and the antialias test on a plain background;
  - `test_sheet.py`: light ink on dark paper.
- **Renders on scratch copies** in /tmp. The ot10 projects were not written.
  - `ot10-quadruped-3` (the W2 design) with `./cadex render` at accepted revision `7de6eea6…`.
  - `w2-2`'s studio video on a copy of `ot10-quadruped-3-w2` with runs/w2-1 excluded, then three decoded frames (0, 5, 10 s) stacked side by side as before, quantised to 128 colours.
- **Docs.** DESIGN-LANGUAGE.md §7 (the backdrop rule replaced, A1's rubric untouched), REVIEW-DESIGN.md §14, §15 and a new §16, CLI.md, and the REPORT.md renders table.

## Result

- **Images.** Committed under `docs/probes/ot10/`:
  - `a8-quadruped-3-hero-dark.png` (195 KB);
  - `a8-quadruped-3-sheet-dark.png` (227 KB);
  - `a8-w2-2-rollout-dark.png` (174 KB).
  The "before" images are the existing `ot10-quadruped-3-hero.png`, `ot10-quadruped-3-sheet.png` and `w2-2-quadruped-rollout-studio.png`, at the same design, view and frames.
- **Timing.** The render of four views plus the 1024 px hero took 15.2 s (hero 4.6 s, sheet 3.1 s), inside A2's 60 s. The engine rebuild is separate, about 150 s.
- **Proxies unchanged:** hardware 0.0 %, sharp edges 11.6 %, 3 materials.
- **Shadow.** The floor at the feet falls from tiles of 28–35 to 6 of 255.
- **Video.** The w2-2 studio video took 189.0 s for 101 frames, against its 300 s bound. It took 153.9 s on the light backdrop, so the floor costs about 23 % more.
- **Tests.**
  - Full CLI suite: 1085 passed, 1 skipped, in 830 s.
  - Engine suite (`pixi run test-engine`): 2282 passed, 53 skipped, in 306 s.

Concerns and assumptions for the next iteration:
- The frozen A1 rubric's T-anchor still says "seamless backdrop". It was not edited, because it is frozen. A future judged probe would see dark renders, which is a change to what the judge sees and needs a recorded re-scoring decision first. None is run this run, since A7 is deferred.
- The dashboard's Chromium playback of the new webm was not re-checked. It lives only in the /tmp scratch copy, not in any project.
- The shadow on the tiny cube and post fixtures is weak, 0.74–0.77 of tile brightness, because a box's foot is hidden under itself. Real designs measure 0.2.
- Next, per the exhaustion policy: the W2 note on what the gait check cannot see, then the C1 closing report, both suites, and reconcile.

Dispatch closed: 1 unit — A8: the studio hero, look, concept sheet and rollout video drawn on the viewport's dark prototype floor from one palette source (ADR-444)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: badcf98713f8da231b785a0c84555f75e02e5762

## State Impact

- target: plain-harbor-3410 — A8 met pending owner tick: scene.py reads the viewport's PALETTE/review.css; studio hero, look, concept sheet and studio video drawn on the #141414 bg with #1c1c1c/#232323 tiles and #3a3a3a grid; test_scene_palette pins it; before/after ot10-quadruped-3 hero+sheet and w2-2 video frames committed ≤300 KB; CLI 1085 passed/1 skipped, engine 2282 passed/53 skipped; nothing re-scored
