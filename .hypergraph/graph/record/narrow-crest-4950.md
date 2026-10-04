---
node_id: 5e68a293-2a40-58bd-a958-808b599daf8e
slug: narrow-crest-4950
title: 'orun2 D2 item 5: exploded view plays the engine''s stages and Cut runs cadex section in the dashboard (ADR-510)'
created_at: '2026-10-03T20:01:10+00:00'
parents:
- polished-lodge-7956
summary: ''
---
## What

orun2 D2 item 5, the section and exploded views (ADR-510, commit `521a9cc9`).

- **Explode.** The dashboard's explode slider plays the engine's own `assembly.exploded_view` record. `review_server.exploded_views` builds pose frames: frame 0 is the assembled model, and each later frame is the previous one with that stage's cumulative poses applied. The page lerps positions and slerps rotations between frames, applies them through `setPoses`, and draws the engine's leader lines while exploded.
- **Section.** **Cut** is `POST api/section`. It runs `cadex section --project … --plane P [--offset-mm=N] --json` as a child, behind the write token and `Origin` check. The page shows the CLI's SVG and clips the viewer's solids, and their shadows, at the same plane and offset. `api/project` carries a `sections` listing, and an SVG is served only when the listing names it.
- **Fixed on the way.** With no simulation trace, `accepted_model` placed each component link at its *declared* placement instead of the solved one. The explosion starts from the solved pose, so the viewer and the engine disagreed. Placement now uses the trace first, then `solved_placement_matrix`, then the declared placement.

## Why

The critic named this unit: the last open part of D2 item 5, section and exploded first, then rollout playback through setPoses, using the engine's exploded_view moves and the section cut with no new geometry path. I did the section and exploded views. **Rollout playback is not in this unit.** It is the next unit and the last piece of D2 item 5. I followed the critic's order and kept to one unit. No new geometry path: the explode uses the engine's record, and the section uses `cadex section`. The viewer's clip is a display-only material clipping plane on the same tessellation the CLI cut.

## Method

- Built the engine suite's EXPLODED_VIEW_SCRIPT on a real engine and confirmed that `result.json` carries `exploded_view` on the output, with `quaternion_xyzw` poses. That check also showed the declared-vs-solved placement defect: `swing` was shown at [0, 0, 40] while the solver put it at [12, 0, 4].
- Server: `_matrix_placement` (row-major 4×4 to xyzw), `exploded_views`, `section_listing`, `write_section_cut`, the SVG route, and `sections` on `api/project`.
- Viewer (`review_scene.js`): `setSection`, `setLines`, `showLines`, and `poses`, `section` and `leaders` in `stats()`. Page (`review.js`, `index.html`): controls in Model settings.
- Tests in `cli/tests/test_dashboard_inspect.py`:
  - Without an engine: both matrix branches, cumulative frames, the section token, `Origin` and body checks, the exact argv including a negative offset passed as one `--offset-mm=` token, the listing, and 404s for unlisted, other-revision and traversal names.
  - Headless Chromium against a real engine:
    - the assembled pose is the solved [12, 0, 4];
    - at the slider's end, every component equals the engine's `final_poses`;
    - at 1.5 stages, `swing` is at [22, 0, 34];
    - the leader lines show only while exploded;
    - a derived XZ cut (2/2 objects) matches its summary and shows the 512 px SVG;
    - the clip removes some model pixels, keeps all of them when the cut is above the model, and leaves none when it is below (the first run left 53,835 shadow pixels until `clipShadows` was set);
    - an explicit XY 7 mm cut typed into the page misses only `base`;
    - Clear restores every pixel.
- Docs: DASHBOARD.md §24 and the Model row, ADR-510, and four SHELL-PARITY rows (`cadex_explode.py`, `cadex_section.py`, `section_view`, `exploded_view`) changed from "to port" to ported, each naming its test. The section *flip* is dropped, with the reason in ADR-510.

## Result

- The dashboard's section and exploded views exist and are proved in the browser against a real engine. The accepted model now shows solved placements when no simulation trace exists.
- Gates on `521a9cc9`:
  - `pixi run test-engine`: 2592 passed, 56 skipped.
  - `pixi run python -m pytest cli/tests` with the GPU hidden: 1343 passed, 1 skipped. I did not identify which test skipped; the suite's only skips are environmental (engine, browser, FFmpeg or transcript gates).
  - `test_dashboard_inspect.py`: 6 passed.
- No protocol or payload change, so the packaged gate was not rerun.
- D2 stays at working. Item 5 still needs **rollout playback through `setPoses`**: play a run's trace in the viewer, with time-based frames and quaternion sign continuity per the `cadex_animate.py` ledger row. That is the next unit and the last thing holding D2 at working. Then A1 and D3.
- The section SVG keeps the CLI's light drawing sheet on the dark page. DASHBOARD.md §24 says so, and it is left as is.
- Each dashboard Cut makes a project commit through the CLI, because `cadex section` commits its `PROGRESS.md` row. That is the CLI's existing behaviour, not a new write path.
- The unreconciled tail is now 1 node.
- No new dependency.

Dispatch closed: 1 unit — dashboard exploded view (engine stages via setPoses) and section cut (cadex section + viewer clip), browser-proved on a real engine (ADR-510)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 521a9cc961de745b5c04bafa14660048bcd281ae

## State Impact

- target: twilight-aspen-1541 — D2 item 5's section and exploded views are ported and browser-proved against a real engine (ADR-510, test_dashboard_inspect.py); accepted placements now prefer solved_placement_matrix; item 5 still lacks rollout playback through setPoses, so D2 stays working
