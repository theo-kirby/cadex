---
node_id: 29403db5-46f1-5954-99bd-ddc0f290444b
slug: happy-valley-9134
title: 'ADR-176: the blueprint becomes a technical drawing — paper theme, radius/angle kinds, dimensions on the sheet'
created_at: '2026-08-30T11:58:13+00:00'
parents:
- green-tree-7595
summary: ''
---
## What

ADR-176: the Blueprint system can now produce a functional technical
drawing without being renamed or forked. Three pieces, one gesture:
declare measurements in the script, then `make_blueprint(theme=
"technical")`.

- **Engine** — `part.measurement` grows `kind="radius"` (the diameter's
  circle published as its half, text `R3.00 mm`) and `kind="angle"` (two
  planar faces or straight edges → a vertex, two rays and the degrees,
  published as `value_deg` with `value_mm` null — degrees are never
  smuggled into a length field).
- **Shell, theme** — `technical` joins the blueprint themes: black lines
  on drawing-paper white. It exposed the one theme-dependent shading
  field: dark-lined themes write `wireframe_color_type='THEME'` (the
  shipped UI theme's wire colour is black) where white-lined themes keep
  `'OBJECT'`.
- **Shell, sheet** — every `make_blueprint` model cell takes a
  `dimensions` flag (omitted: on for orthographic cells). Declared
  measurements project through the cell's own fitted matrices
  (`cadex_sheet.dimension_jobs`) and are drawn drafting-style in the
  dressing pass: extension lines, the dimension line broken around its
  number, radius lines ticked at the rim, angle arcs with upright
  degrees — `cadex_dimension`'s pure geometry (`radius_geometry`,
  `angle_geometry` new), shared verbatim with the viewport overlay.

## Why

Owner direction: the Blueprint should also be able to work like TechDraw
— white background, black text, and real measurement dimensioning
(length, radius, diameter, angle) drawn the way a drawing office draws
them — while keeping the Blueprint name and system. The sheet already
had views, callouts, panels and recipes; what it lacked was the paper
look and the dimensions, and the engine lacked two of the four kinds.

## Method

Engine: `_MEASUREMENT_KINDS` extended; `_angle_frame` picks the vertex
orientation-free (planes' intersection line slid nearest the faces, or
the lines' closest approach) with rays toward the centroids, so the
published opening never depends on OCCT face orientation. A sign error
in the plane-intersection point formula was caught by the live test
(5.38° for a 90° corner) and fixed. Shell: pure halves first
(geometry, jobs, recipe round-trip, theme table), standalone-verified
under the pixi interpreter before the Blender suites ran; the GPU
dressing pass was probed windowed — `_dress_sheet` driven directly with
one job of each kind on the technical theme, PNG inspected by eye and
gated on ink-pixel count.

## Result

- `test_measurement.py`: 7/7 green against a live cadexd — R3.00 mm and
  the 90.00° plate corner (vertex at x=width, z=thickness; rays into
  each face) checked by hand arithmetic; measurements still follow
  `set_params` and the project still reopens.
- Full engine suite: 1919 passed, 47 skipped, 1 failed —
  `test_licensing_compliance` on `demo/biped.cadex/script.py`, verified
  pre-existing at clean HEAD (cc1e711b) in a scratch worktree; not
  touched by this work.
- `pixi run gate`: ok true, themes now
  `[blueprint, cutting_mat, grey, technical]`, 31 pinned fields.
- `bl_mesh_agent.py`: All tests passed, including the two new tests
  (drafting geometry; sheet dimension jobs/legend/meta) — both wired
  into the suite's explicit `main()` list, which silently skips
  unregistered functions.
- Windowed probe `probe_dress_dimensions.py`: app exit 0, 2118 ink
  pixels on a 520x340 sheet; PNG shows all four drawings correct.

Docs: `docs/INTEGRATION.md` (measurement record §), `docs/BLENDER.md`
(four rows), `docs/XSCRIPT.md`, `docs/ROADMAP.md` (ADR-176 item),
`docs/DECISIONS.md` (ADR-176). No new protocol op; the flag rides the
sheet recipe; `shell/` diff stays entirely under `mesh_agent/` + tests.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: cc1e711b0a2877c8dd5ae455ee908ef1bd3b27f5

## State Impact

- target: shy-crane-2573 — the blueprint gains the technical theme (black on paper white; wire channel now theme-dependent) and draws declared part.measurement dimensions drafting-style on sheet cells (per-cell dimensions flag, on by default for ortho cells); the viewport overlay draws radius and angle kinds
- target: forest-wind-0342 — part.measurement gains radius and angle kinds (ADR-176): angle publishes value_deg, a vertex and two rays chosen orientation-free; value_mm stays null for angles
