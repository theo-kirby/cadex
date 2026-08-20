---
node_id: befba01c-2008-51cd-8a73-3fc129a9713a
slug: humble-peak-6095
title: 'Blueprint sheet: 16:9, part callouts, the parameters panel (ADR-153)'
created_at: '2026-08-20T11:38:48+00:00'
parents:
- clever-hill-0361
summary: ''
---
## What

ADR-153: the blueprint sheet reads like a drawing. Three additions —
**16:9 by default** (an optional `aspect` on `make_blueprint`: any
`width:height`, or `auto` for the pre-ADR-153 shapes; the mosaic alone
defaults to `auto` because its shape is the agent's grid), **part-name
callouts** (a leader line from each visible output to its name, on by
default exactly when a cell is exploded, `callouts` true/false anywhere),
and the **parameters panel** as a placeable cell (`{"view": "params"}` —
the declared sliders at their current values, placing and spanning like
any view).

## Why

Owner direction, three asks in one message: the default should be 16:9
rather than square; everything that explodes is a named part and the
names should appear the way an exploded diagram shows them; and the
tunable parameters should be showable as a panel with the sliders at
their positions. All three are composition surface, not new state — the
sheet already renders each cell independently (ADR-151/152), so each ask
lands as one more thing a cell can be or carry.

## Method

`cadex_sheet.py` pure half: `sheet_aspect` parses/refuses the ratio and
carries the mosaic exception; `layout_rects` gained an `aspect`
parameter and tiles the non-square field off the SAME shared integer
boundary arrays, so the tiling invariant is untouched. `callouts_active`
is the default rule (explicit flag wins; omitted means "on when exploded
with factor > 0"); `callout_layout` does side/stack/spacing/drop
arithmetic in cell-local pixels and returns the outer text edge, leaving
glyph measurement to the bpy half because only `blf` knows where a text
ends. `param_rows` mirrors `cadex_backend._bridge_params`'s range
defaulting deliberately, so the panel shows the sliders the user
actually has; `params_panel_layout` collapses overflow into one `+N
more` line.

Bpy half: `callout_anchors` projects each visible output's bbox centre
through the SAME `capture.fit_view` matrices its tile renders with;
`_draw_params_tile` draws the rows into a tile-shaped offscreen on the
ground sampled off a rendered tile (the ADR-151 uniform-ground lesson);
`_dress_sheet` grew the callout pass. `render_blueprint` renders a
callout cell at a wider fit margin (`CALLOUT_FIT_MARGIN = 1.45`) for the
label band, and draws params cells AFTER the flat restore — they are
sheet cells, not scene state, so they skip `apply_view_state` entirely.
A params cell takes only placement keys (camera/scene keys refused by
name) and a script with no parameters refuses it in
`validate_against_model`, which runs before the background refusal and
is therefore gate-testable headless.

## Result

Pure suite green: aspect parsing plus six refusals; the 16:9 triptych
pinned exactly (1024x576, three 341-wide columns); paint-count at 16:9
across every template and count; callout side/spacing/drop arithmetic;
`param_rows` against the bridge's defaulting (including the negative-
default range) and clamping; the schema advertising all three.
`pixi run gate` OK — `sheet.spec_refusals` now 7, the two new ones (a
params cell carrying camera keys, a malformed aspect) landing before the
unchanged headless sentence, and a valid params cell against the
two-parameter fixture validating and only then refusing headless.

Windowed probe against the built bundle (11 sheets): the 16:9 default
with `swing`/`base` named in the exploded column; the panel as a hero
cell and as a 2-row mosaic column, knobs at the right fractions
(reach 12/30, width 40/90, bore 6/14, lift 30/60); `aspect` 4:3 and
`auto` both correct; callouts forced on an unexploded cell and off on an
exploded one; a plain part still degrading to an unexploded rear
three-quarter with no callouts; `leftovers` clean.

One defect the probe found and the fix: at 256 px the triptych's columns
are 85 px wide and the callout text landed ON the model, because a cell
that narrow has no label band. `CALLOUT_MIN_WIDTH = 240` now drops such
a cell's callouts (counted, and said in the tool's note) and skips the
wider fit margin — measured on the sheet, not guessed.

Commit c3eddac7.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: c3eddac7b7660fe58f2c341d273a0a62af4df104

## State Impact

- target: shy-crane-2573 — the composed blueprint sheet gains three surfaces: an optional aspect (16:9 default, auto for the layout-derived shapes, the mosaic defaulting to auto); per-cell part-name callouts with leader lines, on by default for exploded cells, dropped-and-counted below CALLOUT_MIN_WIDTH; and the parameters panel as a placeable cell (view: params) drawn after the flat restore. Protocol untouched; gate spec_refusals now 7.
