---
node_id: af45f6ab-a5d5-56a4-8f7a-5a19154a4d9f
slug: shady-lodge-6077
title: The demo refreshes to the current biped and the card drops the floor
created_at: '2026-08-29T21:53:20+00:00'
parents:
- crimson-vine-9992
summary: ''
---
## What

Two operator corrections to the demo card and payload: the shipped
project was refreshed to the current biped (the working project had
moved 10 accepted revisions past the first copy — reshaped legs, new
`limb_w`/`joint_clear`/`round_r` parameters, accepted `ec4e79e05d19`,
history entry 0055), and the simulation floor no longer appears in the
card at all — the robot stands alone on the viewport ground gradient.

## Method

Re-ran the whole sanitize pipeline on the current project state: store
re-copied (script, params state, policy asset, history pruned to entry
0055), `.blend` re-scrubbed through the bundle (same transcript block,
stray `model.py`, 12 sidecar paths; decompressed byte-check zero
`/Users/`). Card re-rendered by the windowed probe with the floor pair
(`c_floor` + `c_floor Edges`, 400 mm) hidden via `hide_set`. Two probe
findings worth keeping: the floor objects are named `c_floor`, not
`floor` — name-based exclusion missed them, extent-based (>250 mm x/y)
is the robust rule; and `hide_set` alone does not reach an immediately
following offscreen `draw_view3d` — `bpy.context.view_layer.update()`
must run between hide and draw or the hidden object still renders.

## Result

Bundle rebuilt and installed to /Applications; `bl_mesh_agent.py` suite
green; open probe against the installed bundle restores the refreshed
store to its accepted digest with 48 objects. Still uncommitted.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 268cbee80aefa415519365d66c7d23529d1f5a5d

## State Impact

- target: shy-crane-2573 — the shipped demo is the current biped (accepted ec4e79e05d19, history entry 0055) and the card renders the robot alone, floor hidden; sanitize pipeline re-run in full on the refresh
