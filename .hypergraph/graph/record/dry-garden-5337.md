---
node_id: cbbe2cce-6b36-5e4d-89c2-5cf786f0e3ee
slug: dry-garden-5337
title: 'ADR-169: the reward curve reaches the Training editor — the shell''s first plot'
created_at: '2026-08-29T12:30:15+00:00'
parents:
- mild-badger-7944
summary: ''
---
## What

Phase 3 of the local-training-loop round (commit eff5c942, ADR-169): the
shell's first plot. `mesh_agent/cadex_training_plot.py` draws the
`curve` field Phase 2 added to `training-progress.json` as a reward
curve in the bottom 42% of the `CADEX_TRAINING` window region — the
first draw handler on a Cadex space type.

## Why

The Training panel showed a run as numbers; the shape of the reward
curve is what a person actually reads a run by (mg-legs peaked at 1200
of 2000 with nobody able to see it). The North Star arc needs the local
run visibly alive in the editor.

## Method

- Phase 0 probe first: a no-op `SpaceCadexTraining.draw_handler_add`
  against the built bundle, windowed — the callback fired twice on
  redraw of a `CADEX_TRAINING` area, removed once, double-remove raised.
  The rna row existed but had never been exercised; retired before any
  code was written.
- New module by necessity: the gate pins `cadex_training.py`'s import
  closure to `{json, os, bpy}` exactly, so the plot is a separate module
  with a one-way dependency (`plot → training` via `read_progress`),
  gate-asserted in both directions.
- Pattern is `cadex_dimension.py`'s: pure half (`curve_from`,
  `axis_ticks`, `plot_layout`; module-scope import `math` only) holds
  all the arithmetic; bpy half fetches `gpu`/`blf` inside the draw
  callback; idempotent add/remove; registered for the add-on's life
  (a redraw with no run costs one cached stat).
- No operator classes (no-train-button, ADR-084) and no timer
  (`cadex_training.poll` already tags the area).
- Old progress files (no `curve`) degrade to panel-only by construction.
- Registration under `--background` verified green — the handler add is
  safe headless.

## Result

- `bl_mesh_agent.py` suite green (None-cases, monotone x-mapping,
  flat-curve padding, garbage tolerance, tick ladder).
- `pixi run gate` green end to end with the new plot checks.
- `pixi run build-shell` stamps 0.0.5 build 301, module in the bundle.
- `docs/BLENDER.md` file-map row added; `docs/BLENDER-TREE.md`
  untouched — zero inherited-tree lines spent.
- The interactive look with a live run happens in Phase 4 (the balance
  toy), which is the next unit.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: local-training-loop
- commit: eff5c942afd309c3c9a5ee40dcbbe24d5fecb756

## State Impact

- target: late-pond-2851 — The Training editor now draws the reward curve live (cadex_training_plot.py, ADR-169): local and remote runs are visible as a shape, not numbers only.
