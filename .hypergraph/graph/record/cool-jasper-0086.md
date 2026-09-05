---
node_id: e5593f31-29ed-583a-b61b-56ed75a1abb9
slug: cool-jasper-0086
title: 'ADR-177: the exploded view''s duplicates group into an Assembly collection, and the blueprint view pages the stored drawings'
created_at: '2026-08-30T12:37:57+00:00'
parents:
- happy-valley-9134
summary: ''
---
## What

ADR-177, two owner asks on the blueprint/exploded surface:

- **Outliner hygiene for the exploded view.** The engine's exploded-view
  pattern publishes every part twice (the solid and its
  `assembly.component`, whose output name keys `final_poses`), and the
  copies interleaved at the Model root with same-or-similar names.
  `cadex_hydrate` now links every component instance and its wire child
  into an `Assembly` collection that is a **child** of Model — one
  outliner row, one eye-icon hides the lot. Child, not sibling, because
  every walker (find, contract GC, explode posing, camera bounds) uses
  `all_objects`, which recurses — the opposite trade from
  `cadex_collision`'s sibling. Root-linked objects from older sessions
  migrate on the next hydrate; the collection is created with the first
  component and GC'd with the last.
- **The stored drawings become browsable.** The blueprint settings grow
  `source` (`viewport` — ADR-150 styling, unchanged default — or
  `sheets`) and a wrapping `sheet` ordinal; `cadex_drawings.py` (new) is
  the reader: a POST_PIXEL handler paints the region in the theme ground
  and letterboxes the current stored blueprint PNG over it, captioned
  `label vN · i/n · date`, cycled by panel pager or arrow keys. The list
  is read over the protocol (`inspect scope=blueprint`) and cached per
  project root — never fetched from a draw callback; `make_blueprint`
  invalidates and jumps the browser to the sheet it just stored.
- **`inspect_model scope=blueprint` now actually works** — the tool's
  description promised it since ADR-157 while the executor's whitelist
  refused it.

## Why

Owner asks, verbatim in intent: the exploded view "duplicates each
object and leaves it with the same name … no regard for the hygiene of
the rest of the project — just have all the exploded view stuff go into
a collection"; and "click blueprint, toggle between viewport and
outputs, and cycle through all of the blueprints in the blueprint
folder". The duplication mechanism was confirmed in a real project
(`~/arch/pga-v9-exp.cadex` script history: 15 solids + 15 capitalized
component outputs published for one blowout, then ripped out for the
clutter).

## Method

Read the fork's own `gpu_py_offscreen.cc` / `draw_context.cc` before
designing the overlay: `offscreen.draw_view3d` passes no `bContext` and
`drw_callbacks_*` bail on `evil_C == nullptr`, so Python draw handlers
never run offscreen — a stored sheet can never leak into the next
`make_blueprint`, and no suspend hook is needed. Browser mechanics
follow `cadex_landing.py` (permanent guarded handler, lazy gpu/blf,
image→numpy→`gpu.types.Buffer` textures, pure `fit_rect`/`wrap_index`/
`caption_for`). Hydrate routing is two link-site changes plus a
`_link_into` migration helper and a GC epilogue.

## Result

- `bl_mesh_agent.py` (headless, against the built shell): exit 0, "All
  tests passed", including the new
  `test_stored_drawings_browse_from_pure_arithmetic` (wired into the
  explicit main() list; execution confirmed in the log).
- `pixi run gate`: green, including the new Assembly-collection
  assertions in `test_an_assembly_shows_its_solved_placements` (routing,
  wire children, sources stay at root) and
  `test_two_components_share_one_mesh` (collection GC'd with its last
  component).
- No engine change, no protocol change, no new op; `shell/` diff stays
  entirely under `mesh_agent/` + `shell/tests/python/`.

Docs: `docs/BLENDER.md` (hydrate row, new `cadex_drawings.py` row,
tools row), `docs/ROADMAP.md`, `docs/DECISIONS.md` (ADR-177).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: cc1e711b0a2877c8dd5ae455ee908ef1bd3b27f5

## State Impact

- target: shy-crane-2573 — mesh_agent grows cadex_drawings.py (the stored-sheets browser on the blueprint view's new source switch) and cadex_hydrate routes component instances into an Assembly child collection of Model; inspect_model gains the blueprint scope its description had promised since ADR-157
