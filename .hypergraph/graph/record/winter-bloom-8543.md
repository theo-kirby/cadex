---
node_id: 3bf05342-a611-505c-ace5-0e503086643d
slug: winter-bloom-8543
title: 'ADR-178: the blueprint draft editor — make_blueprint stops storing, save_blueprint is the decision, and clicked sections arrive as @cell-N pins'
created_at: '2026-08-30T14:35:17+00:00'
parents:
- calm-flame-0305
summary: ''
---
## What

ADR-178: the blueprint system pivots from store-every-render to a live
**draft editor**. `make_blueprint` keeps its whole composition surface and
stops writing the store — it renders the sheet as the draft, live in the
viewport (blueprint view, source `draft`, switched on by
`cadex_drawings.set_draft`), re-rendering on every call and re-rendering
*itself* when the model rebuilds (view-registry `on_hydrate`, debounced
0.9 s, hidden drafts catch up on next show). The new `save_blueprint` tool
stores the draft the user approved — one shared write path
(`cadex_drawings.save_draft`) with the panel's Save button; Export writes
the PNG anywhere without touching the store. Clicking a view cell of the
draft queues a pin that arrives in the next chat message as `@cell-N (front)`
with the cell's spec — the `cadex_pick` idiom, fourth queue, drained in
`Agent.start_turn`. The day-old ADR-177 stored-sheets browser is removed;
a stored sheet is viewed by `make_blueprint based_on=<name>` loading it
into the draft.

## Why

Owner direction (verbatim asks): a "blueprint editor" that "should live
render what the blueprint will look like and then allow us to save or
export it", "the agent is ... editing the live render and not necessarily
saving at every iteration", "get rid of this blueprint viewer and replace
it with the live preview", and "tag sections of the blueprint in the
editor ... just the same as tagging a vertex or a face". Root cause of
both complaints was one design: every `make_blueprint` stored, so
iteration filled `blueprints/` with near-duplicates and the on-screen
sheet was always a past render.

## Method

Explored three seams before designing: (1) the pin queue
(`cadex_pick._pending_pins` → `consume_pin_notes` → `Agent.start_turn`
suffix — the tag mechanism to copy); (2) the compose pipeline
(`capture.render_blueprint` → `cadex_sheet.layout_rects` per-cell rects,
field-relative, margin added at dress time — the hit-test data, now
returned as `margin`+`theme` in the payload); (3) the window question —
a new Cadex space type is the full BLENDER-TREE §2b price and the cloned
editors are panels-only (`ED_KEYMAP_UI`, empty keymap fn in
`space_cadex_params.cc`), the stock Image Editor is unregistered
(ADR-036), so ADR-096's "an add-on line for a §2b line" rule holds and
the editor lives on the ADR-177 viewport surface. Implementation:
`cadex_drawings.py` rewritten (pure half `fit_rect`/`cell_rects`/
`sheet_point`/`hit_cell`/`map_rect`/`draft_caption`/`section_note`;
draft state, texture, POST_PIXEL draw with hover/tag outlines, two
poll-gated keymap items, Save/Export operators, hydrate hook);
`tools.py` split (`make_blueprint` drafts, `save_blueprint` stores, both
`_ENGINE_TOOLS`, neither `MUTATING_TOOLS`); `cadex_blueprint.py` source
enum `viewport|draft` (`sheet` pager deleted); `ui.py` panel Save/Export;
`spaces.py` header counts section pins with face pins; `agent.py` drains
the fourth queue; `modes.py` teaches the loop in ~210 chars.

## Result

Headless suite green (`bl_mesh_agent.py`, exit 0, "All tests passed") —
new `test_drawing_draft_editor_from_pure_arithmetic` pins the hit-test
round-trip (centre of every mapped cell hits that cell at a real region
size), the margin-band-once rule, queue drain, the tool split, and the
settings (`["viewport", "draft"]`, pager gone); the view-registry pin is
now six views with `drawings` (on_hydrate, no suspend) after
`blueprint`. `pixi run gate` exit 0, `ok: true` — `make_blueprint` still
refuses under `--background` in the stated sentence, and the new
`save_blueprint` no-draft refusal carries the fix. Windowed probe
(bundle + a scratchpad copy of the mgactu project): drafting stores
nothing, the store grows exactly once on save, version 2 on
save-after-redraft, a real-region click hits cell 0 and drains as
`@cell-1` — see probe_draft_report.json in the session scratchpad.
CADEX_OVERLAY grew to ~3.6 KB; its suite cap moved 3500 → 3800.
App reinstalled (`pixi run install-app`, exit 0).

Known limits, stated: drafts are session state (the store holds the
durable versions); the draft editor occupies the viewport rather than a
dockable window of its own — paying §2b for a real drawing space is its
own future ADR if wanted.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: cc1e711b0a2877c8dd5ae455ee908ef1bd3b27f5

## State Impact

- target: shy-crane-2573 — the blueprint pipeline is draft-then-save: make_blueprint renders a live draft in the viewport (re-rendering on rebuild, sections click-taggable into the chat as @cell-N pins), save_blueprint/Save writes the store, Export writes anywhere; the ADR-177 stored-sheets browser is removed, its store-read lesson retained in read_blueprint's _inspect_full path
