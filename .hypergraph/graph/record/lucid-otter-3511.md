---
node_id: 58fd9203-39f4-509a-8d24-d00f79f60856
slug: lucid-otter-3511
title: 'ADR-167: the landing screen in the viewport, and the drone demo in the bundle'
created_at: '2026-08-29T10:00:45+00:00'
parents:
- curious-cloud-7186
summary: ''
---
## What

ADR-167: the app opens onto a **landing screen drawn inside the 3D
viewport** — not a modal, ADR-042 stands and `wm_splash_screen.cc` is
untouched — with a demo-project card and four actions, while the chat
column beside it stays live.

1. **`mesh_agent/cadex_landing.py`** (new): a `POST_PIXEL` overlay on
   `cadex_dimension.py`'s exact mechanics — module-level handle, lazy
   `gpu`/`blf`, pure `landing_layout`/`hit_test` the suite drives headless.
   Input is three add-on keymap items on the 3D View (left-click
   dispatcher that owns the region's clicks while the page is up,
   mouse-move hover, Escape) — no modal grab, so every other editor keeps
   working. Header: wordmark + stamped version (0.0.5) + "AI-native CAD".
   Body: the demo card (blueprint render, hover-highlighted) and New File
   / Open… / Tutorial (stub, tagged "soon") / Start Chatting. Exits: any
   action, Escape, a real file load (`_load_post_handler` →
   `on_file_loaded`), or the first chat message — `Agent.start_turn`
   calls `dismiss()`, the choke point Send and Return share. Navigation
   gizmos are quieted while it shows and restored on dismiss.
2. **The demo project ships in the bundle**: `mesh_agent/demo/` =
   `drone.blend` + `drone.cadex/` (script, script.json, 7 STL assets,
   history; no 51 MB regenerable `script_artifacts/`), ~59 MB all in the
   existing LFS patterns; `install(DIRECTORY scripts…)` carries it with no
   CMake change. Sanitized from `~/arch/wcv12.cadex` (the perf-benchmark
   drone): transcript text removed, `mesh_cadex_source_root` machine path
   dropped, linked `Smooth by Angle` node group made local, both saved
   viewports re-framed to the fitted three-quarter, re-saved add-on-free
   so no handler wrote a path back. `open_demo()` copies blend + store to
   a fresh-numbered matching stem under `~/Documents/Cadex Demo/` and
   opens the copy — the bundle is never opened in place, a saved demo
   session is never clobbered. Card art `demo/card.png` is the demo's own
   blueprint-view three-quarter, rendered with `capture._tile_pixels` +
   `cadex_blueprint.toggle`.

## Why

Operator direction, preparing 0.1.0: a start page like FreeCAD's (in the
UI, clicked through), not like Blender's (modal popup); a demo file card
with a cool thumbnail ("part of the blueprint" was one of the asks); New /
Open / Tutorial-stub / Start Chatting; and keep the current layout's idea —
the viewport hosts the page, the chat stays live beside it.

## Method

Two exploration passes (add-on overlay/keymap/project-open machinery;
demo candidates + how Blender's splash works) before design. One
register-time bug caught by the first windowed probe: `register()` runs in
the restricted context where `bpy.data` is `_RestrictData`, so reading
`filepath` there raised and aborted the rest of `mesh_agent.register()`
(the session lost its save/load handlers). Fix: the show decision defers
through `bpy.app.timers` (the template's own `_apply` idiom), which also
never fires under `--background`, so the gate never sees the page.

Verified:

- `bl_mesh_agent.py` + three tests (layout purity/hit targets/overlap,
  demo payload present and sanitized — no machine path, no .DS_Store or
  .blend1, matching fresh stems — and show/dismiss/yields-to-chat):
  "All tests passed".
- `pixi run gate` after a real `build-shell`: exit 0, `"ok": true`.
- Windowed probes: landing at launch (wordmark 0.0.5, card, four actions,
  gizmos quiet), `open_demo()` landing at `~/Documents/Cadex Demo/drone.blend`
  then `drone-2` on the second click, opening framed with live sliders,
  `orphaned_project` False, root beside the copy. Screenshots
  `landing_launch.png` / `landing_demo_open.png` in the session scratchpad.

## Result

A fresh launch is a start page; one gesture later it is the working app.
Zero inherited-tree lines — add-on, tests, docs only, `BLENDER-TREE.md`
unmoved. Docs: DECISIONS ADR-167; BLENDER.md file-map rows
(`cadex_landing.py`, `demo/`) + "The landing screen (ADR-167)" section.
Deliberate stubs/losses: Tutorial reports "on its way"; the demo copy
lands in `~/Documents/Cadex Demo/` rather than a temp dir so a save is
never lost. Uncommitted with the ADR-164/165/166 work on `114e90ec`.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 114e90ec6d2f973c06f48a3b8e4ccd286b75422f

## State Impact

- target: shy-crane-2573 — the shell opens onto an in-viewport landing screen (demo card, New/Open/Tutorial-stub/Start Chatting, chat live beside it); the wcv12 drone ships sanitized as the bundled demo and always opens as a copy
