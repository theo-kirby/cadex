---
node_id: a42764f1-6c1f-5235-8957-81bf61c3aae0
slug: cool-road-8381
title: 'App shell draft: Blender-style areas, four editors, light theme, hairline render (ADR-534)'
created_at: '2026-10-04T12:34:24+00:00'
parents:
- glad-wood-4169
summary: ''
---
## What
A draft that turns the project page into the app (ADR-534, owner direction 2026-10-04), in Blender's design language. The screen is tiled by areas, and each area shows one editor:
- the 3D viewport: the accepted model or a run's, with rollout playback;
- the 2D viewport: drawings, images, documents and training plots;
- Settings: the project picker, parameters, revisions, theme, render style and layout reset;
- Chat: each message is a design turn.

Areas resize at the gutters, move by dragging a header (dock on an edge or swap in the middle), and split, maximize (Ctrl+Space) or close from the header buttons. Below 700 px, one editor fills the screen and a tab bar switches between them.

The theme is dark by default, with light and system as options. The shaded render is the default, with a hairline diagram style that follows the theme.

## Why
The owner said "this is the app now, not really a dashboard anymore" and asked for Blender's design language: draggable, resizable modules; four of them for now; a light and a dark mode; shaded by default with a hairline/diagram option. Chat is meant to become the agent that controls the whole app; that is not built here.

## Method
- New `review_static/layout.js`: a tree of splits and areas. Editors are singletons, so picking one already shown swaps the two areas. The layout persists in localStorage.
- New `theme.js`: sets `data-theme` before first paint.
- `review_scene.js` gains `setStyle('shaded'|'hairline')`. Hairline renders view normals and depth offscreen, then one fullscreen pass draws ink where depth or normal jumps (crease threshold about 30°) on `--paper`.
- `review.js` was rewritten around the four editors, keeping the existing element ids and the `window.cadexReview` API.
- `test_review_design.py` was rewritten for the area layout, and adds `test_light_theme_is_chosen_kept_and_drawn`.
- Updated DASHBOARD.md §1, §2, §4, §5, §6, §10, §12 and §19, CLI.md, and ADR-534.
- Checked by headless screenshots at 1400×900 and 400×850, a real CDP mouse drag (dock and gutter), and through the /cadex tailscale proxy.

## Result
- `cli/tests` (GPU hidden): 1361 passed, 1 skipped.
- 12 files changed, +1183 / −263 lines.
- No route, write or tool changed. The server only serves two new static files.
- Commit on branch app-shell. It is served at https://sb1x.tailf21f57.ts.net/cadex/ for the owner to try.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: app-shell
- commit: 7c5f88835afcdd062833240ca973116d93099bb0

## State Impact

- target: twilight-aspen-1541 — the browser surface is now the app (ADR-534): a tiled, resizable, movable area layout with 3D viewport (accepted/run model, rollout playback), 2D viewport (drawings, images, docs, training plots), Settings and Chat (design turns); light/dark theme; shaded or hairline render. Draft on branch app-shell, unmerged
