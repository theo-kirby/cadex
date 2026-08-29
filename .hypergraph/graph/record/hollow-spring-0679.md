---
node_id: 3777f7f7-aadd-5857-b3c9-8f56616dffbf
slug: hollow-spring-0679
title: 'ADR-168: outliner in the bottom row, chat at a third, the real mark on the landing screen'
created_at: '2026-08-29T10:48:52+00:00'
parents:
- wandering-mist-0460
summary: ''
---
## What

ADR-168, three parts on the landing/layout surface:

1. **Startup layout re-authored** (`Mesh/startup.blend`, ADR-037's
   mechanism): the chat column is now one third of the window; the bottom
   row is Parameters | Outliner, split in half. Done by windowed probe:
   `area_move`/`area_split` poll on `screen->active_region == NULL`, so
   the cursor was `cursor_warp()`ed onto the edge being moved and one
   event-loop beat waited before the ops ran (two failed attempts first —
   the poll error is context-opaque and the fix is the mouse position).
   Gate now pins four areas AND proportions (chat 0.28–0.38, params and
   outliner sharing the bottom row).
2. **Logo corrected and the stale one deleted.** The landing had used
   `docs/images/cadex-mark.svg` — exactly the VibeCAD-era art ADR-059
   flagged and left "for its own change". Deleted; `landing_logo.png` is
   now the 512 px representation extracted from the shipped
   `cadex_icon.icns` (iconutil), alpha intact — the page shows what the
   Dock shows.
3. **Copy trimmed**: "EXAMPLE PROJECT" overline, caption "Ducted-fan
   drone", footer just "Esc to skip"; the Start Chatting button removed
   as redundant (chat-message and Escape exits unchanged, still pinned).

## Why

Operator direction on seeing the restyled page: split the parameters row
with an outliner, chat at a third; "the logo on the splash screen is the
[VibeCAD] logo which is old — delete it from the project; use the one Mac
already correctly uses for the app icon"; trim the card text; drop Start
Chatting as redundant.

## Method

Re-author probe: dismiss landing (restores gizmos before anything could
save), warp cursor to the chat edge, `area_move` (delta 314 on a 1895 px
window → boundary at 2/3), `area_split` factor 0.5 on the params area,
rightmost half → OUTLINER, `save_homefile`, copy
`<config>/Mesh/startup.blend` into the tree, delete the config copy so
the shipped template stays the source. Suite "All tests passed" (action
order now new/open/tutorial); `pixi run gate` green after a real
build-shell with `startup_areas` = [CADEX_CHAT, CADEX_PARAMS, OUTLINER,
VIEW_3D]; windowed screenshot confirms thirds, outliner, the real mark,
trimmed copy.

## Result

The default window is: viewport (landing on fresh launch) top-left,
Parameters | Outliner under it, chat as the right third. Docs:
DECISIONS ADR-168, BLENDER.md (file-map row, landing section, startup
section), Mesh/__init__.py docstring. Deleted:
docs/images/cadex-mark.svg (closes ADR-059's open item). Uncommitted
with rounds ADR-164..167 on `114e90ec`.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 114e90ec6d2f973c06f48a3b8e4ccd286b75422f

## State Impact

- target: shy-crane-2573 — the default layout is viewport / Parameters|Outliner / chat-at-a-third; the landing screen wears the Dock's own mark (stale cadex-mark.svg deleted, ADR-059 closed) with trimmed copy and no Start Chatting button
