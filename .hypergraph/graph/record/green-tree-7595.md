---
node_id: 34d9f5a5-c387-5bb2-8df1-450deea34386
slug: green-tree-7595
title: Blueprint sheets get names, per-cell shape and text panels (ADR-157)
created_at: '2026-08-20T21:03:18+00:00'
parents:
- humble-peak-6095
summary: ''
---
## What

**A blueprint sheet is now a drawing you come back to.** ADR-157, from one owner
ask: *make a blueprint called something, look at it, come back and change one
view.* Three additions on top of ADR-151/152/153.

- **`name` is the sheet's identity.** `put_blueprint` gains one optional string
  (the **only** protocol change). Storing again under a name that exists appends
  the next `version` of that drawing; `inspect scope=blueprint` resolves a name to
  its newest (`name@2` pins one); the prune keeps each name's newest version past
  `BLUEPRINT_LIMIT`; the store filename carries the name's slug, so
  `export --blueprints` reads as the drawings it holds.
- **`make_blueprint based_on=<name|name@2|ordinal>`** reads that sheet's **recipe**
  back out of the project store and renders it again with only what this call
  passes on top. The recipe is `sheet_recipe`: theme, layout, aspect, max_size and
  the views in *input* form, stored in `put_blueprint`'s free-form `meta`.
- **Per-cell `aspect` and `title`, and `{"view": "text"}`** — a panel of the
  agent's own words (≤ 500 chars, newlines as paragraph breaks), drawn on
  `_draw_params_tile`'s recipe.

## Why

An exploded diagram is long and skinny; in a square cell it is a thin model in a
field of empty ground — the owner's own example. And a sheet that cannot be
revised is a screenshot rather than a drawing: `make_blueprint` could compose
anything and remember nothing, so "the one I made yesterday, but with the section
instead of the top view" meant restating all five cells.

Two decisions carried the design. **The recipe rides `meta`, not a new op** —
ADR-151 put the view specs there to avoid a protocol change, and that is what made
this cheap; `name` is a protocol arg instead *because the engine acts on it*
(resolution and pruning are the store's business, and a store parsing `meta` to
know what to keep would be reading the shell's private record). **The recipe is
the drawn specs, not the raw input** — built after the layout resolved, so
`layout: "auto"` stores as `triptych` and an omitted `views` stores as the five
default cells; that is what makes "change one cell of the default sheet" work.

## Method

Per-cell aspect is honoured **by measurement, not algebra**: the cells compete for
one fixed field, so an exact solve is over-determined the moment two of them ask.
`_boundaries` now takes weights instead of a count (its last boundary is still
exactly `total`, so no-gap/no-overlap still holds by construction), `_place_rects`
is one placement pass, and `layout_rects` places, measures the shape each cell came
out at, scales the track that cell owns toward its ask, and places again —
`ASPECT_PASSES = 3`, clamped by `MAX_CELL_SCALE = 4`, and an ask that would starve
a neighbour below 8 px is dropped whole. A cell owning a full track takes its scale
directly; a cell whose width *and* height are both free (grid, mosaic, the
triptych's left stack) takes `sqrt` on each axis.

Verification, in the order it was run:

- `pixi run python -m pytest src/Mod/cadex/cadex_tests` — **1902 passed, 33
  skipped**, including four new `test_blueprints.py` tests (naming, versioning,
  slug fallback, the name-protecting prune) and a named round trip over the wire in
  `test_cadexd_lifecycle` (`0002-gearbox-overview-v1.png`, version 2, recipe read
  back through `inspect`).
- The **packaged** gate against a freshly staged payload
  (`CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64`) — 14 passed,
  ADR-023's rule honoured for a protocol change.
- `pixi run python -m pytest cli/tests` — 83 passed.
- `tests/python/bl_mesh_agent.py` (the pure half, ~5 s per run) — all passed,
  including the new `test_blueprint_sheets_are_named_shaped_and_revisable`.
- `pixi run gate` — `"ok": true`, `"sheet": {"outputs": 8, "spec_refusals": 9}`.
- A **windowed probe** of the built bundle, because the gate is `--background` and
  this feature is pixels.

## Result

**The three properties the tests pin**, each a property rather than an example:
weighted tiling paint-counted over random asks across five templates at 256/1023 px
and three sheet aspects (0 gaps, 0 overlaps, 0 slivers); a 1:3 ask on a triptych's
full-height column landing **within 0.05 of 1:3** where the unweighted layout was
0.79; and `normalize_views(recipe_views(specs)) == specs` on a composed sheet, on
the **default** sheet and on a mosaic — the round trip is what makes a stored sheet
revisable rather than merely recorded.

**The probe** ran five sheets against a three-output parametric model: a named
sheet with a titled cell, a text panel and two shaped cells; the same name
re-rendered with `based_on` and *only* a theme passed, which came back as version 2
with every view inherited; a third version with the top view swapped for the
parameters panel; the unnamed default sheet; and that default re-based by ordinal
under a new name. Filenames `0001-probe-sheet-v1.png … 0005-default-plus-notes.png`,
versions 1/2/3 under one name, each recipe ~1.3 KB of a 16 KB cap. The text panel
drew its heading, its paragraph break and a hyphenated part number wrapped at real
glyph widths.

**The honest numbers on shape.** The full-height column asked 1:3 and was drawn
**1:2.97**; the text panel in the shared left stack asked 1:2 and was drawn
**1.31:1**, because in a three-cell column the width is not that cell's to spend.
Both appear in the caption the agent reads back, and the tool description now says
to put an extreme shape in a column of its own. A variant that spent the full ask
on the stacked cell's own axis reached 0.98 but squashed its two innocent siblings
to 96 px strips; it was measured and rejected.

**One defect found that was not this change's.** The probe showed the
**parameters** panel drawing its first slider row *through* the word "parameters" —
the cell's label is drawn over the tile by the sheet dressing and
`_draw_params_tile` never knew about that band. Fixed here (`params_panel_layout`
takes the same `top_pad` the text panel needed) because this change made it visible
and the parameter existed anyway. Re-probed after a shell rebuild: clear.

**Not built, deliberately.** No per-cell *patch* surface — revising one cell means
passing the views list back with one entry changed, and the recipe the agent reads
is what it edits; a patch language would be a second spelling of `views` with its
own semantics to get wrong. `MAX_META_BYTES` went 8 KB → 16 KB to hold the recipe,
with `trim_meta` dropping the optional records (rects, then the per-cell record)
before the engine can refuse an already-drawn sheet — the recipe is what a trim
defends.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: e5c2d6b6ee9d56ae1eba5994b933495f026ec365

## State Impact

- target: shy-crane-2573 — make_blueprint becomes revisable and gains two cell surfaces: a name that is the sheet's IDENTITY (re-render under it and the store keeps the next version), based_on reading a stored recipe back through cadex_backend.read_blueprint, a per-cell aspect honoured by measure-and-replace in weighted layout_rects boundaries (the caption reports the shape DRAWN, not the shape asked), a per-cell title, and {view: text} as a second panel kind beside params. cadex_sheet gains parse_aspect, wrap_text/text_panel_layout/_draw_text_tile, recipe_view(s)/sheet_recipe/trim_meta and PANEL_VIEWS; recipe round-trip is test-pinned. An ADR-153 defect fixed in passing: params_panel_layout now takes top_pad, so the first slider row no longer draws through the cell's own label. Gate spec_refusals 7 -> 9.
- target: forest-wind-0342 — the blueprint store gains identity: put_blueprint takes an optional name (17 -> 17 ops, one new optional arg), entries carry name and version, resolve_blueprint matches an exact name (newest version, name@2 pins one) before a revision prefix, the stored filename uses the name's slug, and the prune keeps each name's newest version past BLUEPRINT_LIMIT. MAX_META_BYTES 8 KB -> 16 KB so the shell's re-render recipe rides meta. Engine suite 1899 -> 1902 passed / 33 skipped.
