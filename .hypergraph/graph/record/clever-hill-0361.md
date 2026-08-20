---
node_id: a9853d77-8af0-5492-ac94-ea5f4f3e9a11
slug: clever-hill-0361
title: 'Blueprint sheet: only and the mosaic layout (ADR-152)'
created_at: '2026-08-20T10:38:26+00:00'
parents:
- wild-walrus-5718
summary: ''
---
## What

ADR-152: the blueprint sheet gains its curation surface. Per-cell
**`only`** (the isolate: show just these outputs, everything else hidden)
and the **`mosaic`** layout (freeform placement: every view carries
`cell [row, column]` and an optional `span [rows, columns]` on a grid
inferred from the placements; unclaimed cells stay uniform ground, so
asymmetric compositions work). The tool description now tells the agent
to curate sheets for what was built — a gearbox as a big exploded stack
beside a mid-cut section with the casing hidden — rather than front/side
boilerplate.

## Why

Owner direction: sheets should be super flexible, non-uniform grids
included, because every build composes differently. The owner floated
Blender local collections for per-viewport visibility; not needed — the
renderer already applies each cell's state sequentially (ADR-151's
snapshot → apply → flat restore), which is strictly more general (a
per-cell section or explode could never ride a collection trick).

## Method

`cadex_sheet.py`: `only` validated (mutually exclusive with `hide`, names
must be declared outputs) and normalized into the complement `hide` tuple
the apply path already honours — isolating costs the state machinery
nothing; the spec keeps `only` for the legend ("only swing shown") and
the meta. `cell`/`span` validated per view (1-based pairs, `MAX_GRID = 6`
cap); `choose_layout` refuses partial placement and overlap (both views
named), routes `auto` to `mosaic` when cells are present, and allows
holes on purpose; `layout_rects` gains the mosaic branch — extent
inferred from the placements, field aspect columns:rows with the longest
edge `max_size`, rects off the same shared integer boundary arrays the
templates use. This reverses ADR-151's "templates, not freeform spans":
the owner overruled the premise, and the tiling invariant survives as
refusal + paint-count rather than by construction — the no-hole half
dropped deliberately. `tools.py`: `only`/`cell`/`span` in the schema,
`mosaic` in the layout enum, the curation rewrite of the description.

## Result

Pure suite green: the only-complement and meta shape, both `only`
refusals; mosaic rect arithmetic pinned exactly on a spanned 3×3 with a
hole (paint-count: no overlap, hole present); aspect follows the grid
(1×2 → 1024×512); ten refusal sentences all told. Gate green including
the new `only` apply/restore round-trip against the bundled engine.
Windowed probe: the gearbox-shaped mosaic — a 3×2-span exploded
three-quarter beside an isolated-`only` cell and a sectioned cell, the
unclaimed corner clean uniform ground, nothing left behind after
restore.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: e5671d1345d481885845577e982d98d4c0b73aa4

## State Impact

- target: shy-crane-2573 — the sheet gains its curation surface (ADR-152): per-cell only (the isolate, normalized into the complement hide so the state machinery is untouched) and the freeform mosaic layout (cell [row, column] + optional span on a grid inferred from the placements, auto-routed when cells are present, holes allowed as uniform ground, overlap and partial placement refused, 6x6 cap) — reversing ADR-151's templates-only call on owner direction, with the tiling invariant surviving as refusal + paint-count; the tool description now pushes per-build curation over front/side boilerplate
