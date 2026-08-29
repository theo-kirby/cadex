---
node_id: 976265ff-2f76-5746-9f76-172b0b3cc28e
slug: tender-crane-5909
title: The chat row is for the chat, and the message box sits on the floor — ADR-164
created_at: '2026-08-29T08:47:13+00:00'
parents:
- weathered-sand-9705
summary: ''
---
## What

Two chat-editor quality-of-life defects fixed and one relocation that follows
from them, together ADR-164.

1. The message box ("Ask for a change") and its button row floated ~90 px
   above the bottom of the window. The chat editor's execute region is
   `RGN_ALIGN_BOTTOM` but was a fixed `6 * HEADERY` tall, and panel content
   draws from a region's top, so the slack sat *under* the input as dead
   region rows.
2. The button row was glued to the box (an `align=True` column) and had grown
   to sixteen buttons, most of which act on the model or the viewport rather
   than on the chat.
3. Rebuild Model and the view switches (Script, Wiring, Collision Shapes,
   Dimensions, Section View, Exploded View, Blueprint) moved to a new
   **Interface** section at the bottom of the parameters panel
   (`ui._draw_interface`), joining the section-cage/section/explode/blueprint
   controls already there. The chat row keeps the gather group, the
   parameters toggle (the door), New Chat and Send/Stop.

## Why

Operator report, verbatim intent: the input box should sit at the bottom of
the window, the buttons under it need padding, and only chat-related buttons
belong under the chat bar — the rest belong in the parameters panel,
expanding the section that already held Section Cage / Section View /
Exploded View.

## Method

Diagnosed with a windowed probe against the built bundle (`--factory-startup
--app-template Mesh`, screenshot + region-geometry JSON): execute region
`y=23 h=156`, content top-anchored, ~90 px dead below. Fix in three parts:

- `space_cadex_chat.cc`: execute region gets `RGN_FLAG_DYNAMIC_SIZE |
  RGN_FLAG_NO_USER_RESIZE` — the project editor's exact recipe — so the
  region hugs the box and its row. `cadex_chat_init()` enforces the flags on
  areas loaded from saved layouts (the app template and older user files
  carry the fixed-height region they were saved with), the way
  `BKE_screen_header_alignment_reset()` pins header alignment. Region-edge
  resizing is replaced by the text box's own grip: more visible lines is more
  content, and the region follows.
- `mesh_agent/ui.py`: `CADEX_CHAT_PT_input` separates box and row with a
  plain column + `separator(factor=0.5)`; `draw_chat_buttons` shrinks to
  gather/params/turn; new `_draw_interface(layout, context)` draws Rebuild
  Model, the four view toggles (two per row) and the four pre-existing
  view-control boxes, and is drawn on *both* branches of the parameters
  panel — a view is arrangeable regardless of sliders.
- `bl_mesh_agent.py`: the one-row test now pins the eight relocated buttons
  *out* of the row and *into* the Interface section; `_RecordingLayout`
  gained `box()`.

## Result

- Windowed probe after `pixi run build-shell`: input + padded row flush at
  the window bottom, Interface section rendering in the parameters panel
  (screenshot-verified).
- `pixi run gate`: green, `ok: true`, slider-latency median 0.54 s within
  the 0.65 s bar.
- `bash package/app/build_app.sh gate tests/python/bl_mesh_agent.py`:
  "All tests passed", exit 0 (live turn skipped as designed).
- Docs updated in the same change: `docs/DECISIONS.md` (ADR-164),
  `docs/BLENDER.md` (row table, execute-region description, parameters
  section, date), `docs/BLENDER-TREE.md` (chat editor line count 202 → 220,
  date). The ADR-074 one-row invariant is narrowed, not repealed: every
  *chat* action is still in one row that never changes width.
- The diff is uncommitted at record time, on top of `114e90ec`.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 114e90ec6d2f973c06f48a3b8e4ccd286b75422f

## State Impact

- target: shy-crane-2573 — The chat editor's execute region is dynamic-size (ADR-164): the message box and its padded button row hug the bottom of the window, enforced in cadex_chat_init for saved layouts. The chat row carries only chat actions (gather, the parameters toggle, the turn); Rebuild Model and the view switches live in the parameters panel's Interface section (ui._draw_interface), which draws whether or not the model has sliders.
