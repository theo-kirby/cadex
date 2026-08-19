---
node_id: 39f11255-6b36-5e06-8f25-be1e0657c11e
slug: morning-walrus-8074
title: 'Blueprint Sheet v2: composed views and drawing-sheet dressing (ADR-151)'
created_at: '2026-08-19T19:55:38+00:00'
parents:
- windy-wolf-5012
summary: ''
---
## What

Blueprint Sheet v2 (ADR-151): the stored blueprint sheet becomes
**agent-composed and dressed like a drawing**, all of it shell-side. The
agent picks up to 6 views — the six named orthos, the three-quarter, or a
custom azimuth/elevation — and gives each cell its own hidden outputs,
exploded factor and section override; layouts are five templates with
**hero-right** the default (three small orthos stacked left, the big
three-quarter filling the right two-thirds). The stored PNG gains
drawing-sheet dressing: a faint page grid with border zone marks (1, 2, 3
along the top, A, B, C down the left), the project name top-left, and
`CADEX <version> · rev · date · theme` bottom-right. Theme grounds darkened
~20–25%. The live viewport blueprint is unchanged (owner choice). Protocol
untouched: specs travel in `put_blueprint`'s free-form `meta`.

## Why

Three owner asks on ADR-150's sheet: slightly darker themes; the fixed 2×2
made the perspective too small; and "hide the housing so the insides show"
had no way in. The tool already returns the image, so a composable sheet
lets the agent look and iterate.

## Method

New `mesh_agent/cadex_sheet.py`, split on the module template's pure/bpy
rule. Pure half: `normalize_views` (full-sentence refusals; ≤6 views;
duplicates allowed), `choose_layout` (auto → single/hero/row/grid),
`layout_rects` (shared integer boundary arrays — no-gap/no-overlap by
construction), `zone_grid`/`title_lines`/`cell_legend`. Bpy half:
`snapshot_state` once → `apply_view_state` per cell (hides via
`obj.hide_set` — `hide_viewport` is hydrate's channel; explode then
section, section last because the wire clip bakes the plane per-object) →
`restore_state`, ONE flat exception-hardened restore in the renderer's
finally; `quiet()` added to cadex_explode/cadex_section exposing their
settle guard. `_dress_sheet` is a second offscreen pass on the in-tree blf
recipe (bind → clear → pixel-ortho projection; DejaVuSansMono via
system_resource, blf.size two-arg; alpha forced opaque after FLOAT
readback). `capture.py`: `NAMED_VIEWS`, `fit_view` and `composite_rects`
extracted with `view_matrices`/`composite_2x2` as wrappers (pure suite pins
both equivalences); `render_blueprint` validates specs BEFORE the
background refusal. `cadexd_client.engine_version()` reads the manifest
version the launcher reader always dropped. Tool schema: `views` (flat,
one nesting level) + `layout`.

## Result

Pure suite green including the new `test_blueprint_sheets_compose_from_
pure_arithmetic` (paint-count tiling over every template × count 1–6 ×
sizes {256, 1023, 1024}; every refusal sentence; hero strictly largest and
on the right). Gate green including `test_sheet_state_applies_and_restores`
— refusal ordering pinned, state round-trips bit-for-bit against the
bundled engine with live toggles on and off, accepted revision unchanged.
Engine suite 1869 passed / 33 expected skips; cli 83 passed. Windowed
probe (uncommitted, ADR-124 precedent): six sheets rendered — hero cell
large right, hidden output absent from its cell only, exploded cell with
leader line, zone marks and title block legible at 256 px, nothing left
behind after restore. Two probe-found fixes landed: zone numbers yield to
the project title, and the bottom title line drops middle segments to fit
small sheets. One gate-found lesson: the Section Cutter's matrix is
derived from bounds at refresh time, so bit-equality is asserted against a
reproducible live value (explosion on before section in the fixture) — a
restore that recomputes a stale derived artifact is more correct than the
staleness.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 3130dfa7809a591bb1a931ae8dc1c9f067287b5f

## State Impact

- target: shy-crane-2573 — make_blueprint is agent-composed (ADR-151): up to 6 views (named orthos/three-quarter/custom azimuth-elevation) with per-cell hide (hide_set, never hydrate's hide_viewport), exploded factor and section override, five layout templates defaulting hero-right; the stored PNG is dressed (zone-marked page grid, project name, CADEX version/rev/date/theme from the engine manifest via cadexd_client.engine_version); themes darkened; cadex_sheet.py holds the spec/tiling/dressing pure half and the flat snapshot/apply/restore state machinery; protocol untouched (specs ride put_blueprint meta)
