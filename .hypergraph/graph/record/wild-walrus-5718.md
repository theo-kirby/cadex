---
node_id: 8135a596-d5b7-59eb-a585-ffa1393f62af
slug: wild-walrus-5718
title: 'Blueprint sheet: triptych default and uniform ground (ADR-151 addendum)'
created_at: '2026-08-20T09:09:00+00:00'
parents:
- morning-walrus-8074
summary: ''
---
## What

The ADR-151 addendum, from the owner's first session with the composed
sheet: the default becomes a **triptych** (front, top, bottom stacked down
the left third; the three-quarter perspective filling the centre third;
the same perspective spun 180° about Z — azimuth 225 — fully exploded in
the right third), and the sheet ground becomes **one uniform colour** (the
darker margin band is gone). A sixth layout template `triptych` is exposed
to the agent as well; the dressing text stays where it was.

## Why

Owner direction after using v2: three columns with the exploded rear
perspective as its own full-height column, and "make everything the same
colour — we don't need the dark blue outline". The band/field mismatch was
already a known nit (raw linear clear vs colour-managed tiles); the owner
call settled it.

## Method

`cadex_sheet.py`: `LAYOUTS` gains `triptych` (three equal columns by the
shared-boundary arrays; views[:-2] stack left, views[-2]/views[-1] take
full-height centre/right; <3 views refused, a direct call with 2 degrades
to `row`); `DEFAULT_VIEWS` becomes the five-view list with the last spec
labelled `exploded`; `display_color` (pure sRGB encode) is the fallback
ground; `_dress_sheet` takes a `background` in display space;
`cell_legend`'s horizontal words moved to edge-touch logic (a centre
column's midpoint rounds to a half that left/right lies about).
`capture.render_blueprint`: an omitted `views` routes `auto` to
`triptych`, strips the default explode when the model declares no exploded
view or a simulation is baked (relabelling the cell "rear three-quarter"
— the default must never refuse a plain part; explicit specs stay
strict), and samples the sheet ground off the composited field's corner
pixel. `tools.py`: layout enum + description updated.

## Result

Pure suite green (triptych in the paint-count loop and pinned at 5×1024:
left cells 341 wide, centre 342×1024, right 341×1024; the triptych-of-two
refusal; `display_color` range/clamp pins; the triptych legend reads
"large, centre" / "right"). Gate green, unchanged tests. Windowed probe:
the default triptych renders as asked on the exploded fixture (rear cell
exploded with leader line) and degrades on a plain box (right column
"rear three-quarter", unexploded, no refusal); the ground measured
uniform to the pixel — (53, 82, 131) at band and field alike, on all
three themes and at 256 px.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: c51349ddccdbf92c9ab9d7a080d444697b552ead

## State Impact

- target: shy-crane-2573 — the default blueprint sheet is the triptych (ADR-151 addendum): front/top/bottom stacked down the left third, the three-quarter perspective centre, the rear (Z+180) perspective fully exploded right — degrading to unexploded (never refusing) on a model with no exploded view or a baked simulation; the sheet ground is one uniform colour, sampled off the colour-managed tiles (display_color as pure fallback) so the darker margin band is gone; triptych is a sixth layout template the agent can also request
