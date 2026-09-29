---
node_id: 000f21d0-9668-5f89-9804-fcb6daa56826
slug: peaceful-sail-5197
title: The app shows and makes the studio renders, and plays run videos (ADR-452)
created_at: '2026-09-29T12:25:59+00:00'
parents:
- staid-nest-0170
summary: ''
---
## What
GUI-parity slice 7 (ADR-452): a Renders panel in the Training editor shows the studio hero (thumbnail), its design relation and the sheet's numbers, opens hero/sheet in the system viewer, and Render Now draws them with the engine studio into `review/render/`; a Play Video button on runs with a video on disk.

## Why
View renders and videos in the app as in the dashboard (warm-spire-8762), and make renders without the CLI.

## Method
- New `mesh_agent/cadex_presentation.py`: the dashboard's render-selection rule over `summary.json`; `render_now`/operator run `cadex_studio.run(kind="render")` on the accepted display with measured fit/inventory (worker thread + timer).
- `cadex_runs.video_file` resolves the newest `video.json` entry inside the run; `wm.path_open` plays it.
- `cadex_backend.hydrate` keeps the reply `digest` in the accepted record for the sheet.
- Bug found and fixed before commit: `import bpy.utils.previews` inside a function shadowed `bpy` and broke `unregister`.

## Result
- No-engine suite: exit 0, 1259 ok (selection rule's three cases, video containment, panel draw).
- `pixi run gate`: new `test_render_now_draws_what_cadex_render_draws` passes (6.1 s; hero, sheet, summary written; presented as current). Slider median 0.55 s. Only the 8 pre-existing restore-lockout failures.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: gui/renders-videos
- commit: 1a4af8d3ad9e1f64f577e1d78ede373bba21c1b2

## State Impact

- target: shy-crane-2573 — the Training editor has a Renders panel (hero thumbnail, relation, sheet numbers, open in viewer) with Render Now through the engine studio into review/render/, and runs with a video get Play Video (ADR-452)
