---
node_id: 0235ccab-a988-5ab0-9903-199421ab8209
slug: civic-glade-9153
title: One grid in the Interface section, and no open-a-view operators — ADR-165
created_at: '2026-08-29T09:04:58+00:00'
parents:
- tender-crane-5909
summary: ''
---
## What

Operator feedback on ADR-164's landing, two refinements together as ADR-165:

1. **One grid in the Interface section.** The six viewport toggles drew in
   two styles — the four relocated ones as a two-per-row grid, the four
   pre-existing controls (Section Cage, Section View, Exploded View,
   Blueprint) as freestanding full-width boxes. Unified into one two-per-row
   grid (Collision Shapes | Dimensions, Section Cage | Section View,
   Exploded View | Blueprint), each depressed while on; a toggle that is on
   and has settings gets a labelled box under the grid.
2. **No open-a-view operators, buttons or classes.**
   `mesh_agent.toggle_params` (+ `ui.params_area`, `PARAMS_SPLIT`),
   `mesh_agent.show_script` (+ `spaces.script_area`) and
   `mesh_agent.toggle_wiring` (+ `wiring_ui.wiring_area`, `WIRING_SPLIT`)
   deleted — ~230 lines of split-an-area machinery. Editors are opened with
   Blender's own editor dropdown and tiling, which every area already has;
   the parameters editor is open in the default layout anyway. Standing
   rule going forward: no button whose job is to show or hide an editor.
   The chat row is now gather + turn only.

## Why

Operator, on seeing ADR-164 in the app: unify the old boxes with the new
grid, and drop the panel-opening buttons entirely — "that can just be done
through the normal blender window opener and tiling manager. We don't need
any in the future."

## Method

Pure Python subtraction plus one draw restructure in
`mesh_agent/ui.py::_draw_interface`; operator deletions in `ui.py`,
`spaces.py`, `wiring_ui.py` with their registration rows. The wiring editor
stays reachable because `CadexWiringTree.get_from_context` (ADR-074)
populates a freshly picked Wiring editor on first redraw; the script mirror
is picked in a stock Text Editor. The one-row gate test now also pins the
three operator classes as absent from `bpy.types`. Docs:
`docs/DECISIONS.md` (ADR-165), `docs/BLENDER.md` (row table, Interface
description, spaces.py/wiring passages rewritten; the
ui_type-before-node_tree ordering the deleted wiring toggle had learned is
preserved there in prose).

## Result

- Windowed probe on the rebuilt bundle: one uniform grid under Rebuild
  Model, chat row slimmed to gather + turn, input still flush at the window
  bottom (screenshot-verified).
- `pixi run gate`: exit 0, `"ok": true`.
- `bl_mesh_agent.py` suite: "All tests passed", 979 checks, including the
  new pins (six toggles out of the row, seven controls in the Interface
  section, three operators unregistered).
- ADR-164's "the parameters toggle stays because it is the door" clause is
  superseded by ADR-165; the diff is uncommitted at record time, on top of
  `114e90ec` together with the ADR-164 work.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 114e90ec6d2f973c06f48a3b8e4ccd286b75422f

## State Impact

- target: shy-crane-2573 — The Interface section is one two-per-row grid of viewport toggles with settings boxes under it (ADR-165); the open-a-view operators (toggle_params, show_script, toggle_wiring) are deleted, editors are opened with Blender's editor dropdown and tiling, and the standing rule is no future show/hide-an-editor button. The chat row is gather + turn only.
