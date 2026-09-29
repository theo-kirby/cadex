---
node_id: 7cfd1630-2648-5f90-bdbb-2502ae0dc5ea
slug: hidden-bloom-1188
title: 'ot10: render clustering grid sized from drawn parts, not the floor — hexapod-12 cell 1.465→0.271 mm, 352k triangles, 14.5 s (ADR-439)'
created_at: '2026-09-29T03:49:18+00:00'
parents:
- sweet-harvest-8650
summary: ''
---
## What
The render's vertex-clustering grid is now sized from the extent of the parts that are drawn. Before, the world floor set it (ADR-439, commit `ab60e2c7`). `render.snapshot(reply, environment)` leaves out the environment names when it computes the extent. The floor is still read, clustered and counted against the budget. `acquire_snapshot` reads the accepted fit after its rebuild to learn the names, and the bridge's `look` passes the fit it already holds. `summary.decimation` now also reports `extent_mm` and `extent_excludes`.

## Why
The critic named this unit, and it is the renderer half of hexapod-12's diagnosed miss (sweet-harvest-8650). Its 3,000 mm floor drew the robot on a 1.465 mm grid. I did what the critic asked, with no deviation.

## Method
- Added `render.world(fit)`, the helper `classify` now uses too. Added an `environment` keyword to `snapshot`. If every part is environment, the extent falls back to all parts. A fit that cannot be read leaves every part in the extent, which is the old behaviour, rather than failing the render.
- Two regression tests in `cli/tests/test_render.py`. The first puts a 10 mm grid beside a 3,000 mm floor and checks the cell equals the one for the grid alone. Left unnamed, the floor gives exactly 3000/2048 mm and the grid loses more than 90% of its triangles. The second checks that `acquire_snapshot` takes the floor from the fit, and falls back when the fit is unreadable. Both fail on the previous source: I checked with `git stash`.
- Re-rendered `ot10-hexapod-12` from a new copy under `/tmp`, at the same accepted revision and the same hero view. Its original project and `/tmp` copy were not touched.
- Checked `decimation` against the robot's own extent in every ot10 render summary under `/tmp`.

## Result
- **Hexapod-12, same revision, same view.**
  - Cell: 1.465 → 0.271 mm.
  - Drawn triangles: 52,303 → 352,317.
  - Drawing time: 4.5 s → 14.5 s (hero 1.7 s → 3.1 s), well inside A2's 60 s. The whole `cadex render` took 4 min 59 s of wall time, mostly the engine rebuild.
  - Heroes: before is `docs/probes/ot10/ot10-hexapod-12-hero.png` (the judged image, 140 KB). After is `ot10-hexapod-12-hero-grid-after.png` (130 KB). The lumpy tibias are smooth in the after image.
  - Proxies: P1 moved 0.0038 → 0.0036. P2 (0.1844) and P3 (3) did not move.
- **Nothing is re-scored.** Hexapod-12's 12 of 21 stands.
- **Finding (not a score):** every earlier decimated ot10 render had a floor wider than its robot, so each would now draw on a finer grid than the one it was judged on:
  - hex3's baseline: 500 mm floor over 173 mm;
  - hexapod-5 to 11, quadruped-3 and 4, biped-1 and 3: 800–1,200 mm floors over 174–306 mm.
- **Tests and docs.**
  - CLI suite: 1071 passed, 1 skipped (the review-host skip).
  - `docs/CLI.md`, `docs/probes/ot10/README.md` and `REPORT.md` (defect 8, now marked fixed) are updated.
  - No engine or payload file changed, so I did not re-run the engine suite or the packaged gate.
- **Next.** The other half of the diagnosis is the design: bare splined horns (T3). That is a prompt or reference matter to diagnose before the next A5 turn.
- **Tail:** two unreconciled records.

Dispatch closed: 1 unit — render clustering grid sized from drawn parts, not the floor (ADR-439); hexapod-12 cell 1.465→0.271 mm, 52k→352k triangles, 14.5 s; before/after heroes committed; earlier renders' finer-grid effect recorded as a finding, nothing re-scored

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: ab60e2c7253a32eb45b269904cfd46e78e2b3f9e

## State Impact

- target: damp-moon-9297 — The render's clustering grid is sized from the non-environment parts' extent (ADR-439, commit ab60e2c7): a declared floor no longer coarsens the robot; ot10-hexapod-12's same revision draws on a 0.271 mm cell (was 1.465) as 352,317 triangles in 14.5 s; earlier decimated ot10 renders would draw finer than they were judged, recorded as a finding, nothing re-scored
