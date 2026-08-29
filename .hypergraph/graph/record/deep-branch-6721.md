---
node_id: a50b1a94-cbc9-5c5b-9c09-964fd999458a
slug: deep-branch-6721
title: 'ADR-172: the default viewport look — cavity on, gizmos off, overlays on but bare'
created_at: '2026-08-29T21:01:47+00:00'
parents:
- hollow-spring-0679
summary: ''
---
## What

The default viewport look changed (ADR-172): the app now opens with cavity
shading on (SCREEN type over the unchanged solid/matcap), transform gizmos
off, and overlays on but bare — no floor, no ortho grid, no X or Y axis,
only the Z axis line.

## Why

Operator direction, the fourth sitting on the startup surface (after
ADR-037, ADR-042, ADR-168). Cavity makes edges and pockets readable on the
flat matcap; the gizmo and the floor/grid are chrome the product does not
want at rest; the Z axis alone keeps an up-reference in an otherwise bare
viewport.

## Method

Same mechanism as every startup-look change since ADR-037: the look *is*
`shell/scripts/startup/bl_app_templates_system/Mesh/startup.blend`. A
headless script run inside the built bundle
(`Cadex --background --factory-startup --python restyle_startup.py`) opened
the template, set `show_gizmo=False`, `shading.show_cavity=True`,
`overlay.show_overlays=True`, `show_floor=False`, `show_ortho_grid=False`,
`show_axis_x/y=False`, `show_axis_z=True` on the one VIEW_3D space, and
re-saved the file (244 KB, git-LFS). Knock-ons taken in the same change:
`test_startup_layout_is_the_shipped_file` pins the new look in place of the
old overlays-off check; `cadex_blueprint.PRODUCT_LOOK` (documented equal to
the gate-pinned startup look) follows, with the pure suite's equality
assertion extended; the blueprint docstring drops its claim to be the only
view that turns overlays on; `docs/BLENDER.md` updated in both places it
described the look.

## Result

`pixi run gate` green (`ok: true`, startup and blueprint tests included);
`bash package/app/build_app.sh gate tests/python/bl_mesh_agent.py` green
("All tests passed"); `test_licensing_compliance.py` green (10 passed,
1 skipped). The blueprint view's behaviour is unchanged — it always pinned
every sub-overlay explicitly, so the new default alters only what it
captures and restores. Files: `Mesh/startup.blend`,
`bl_mesh_agent_cadex.py`, `bl_mesh_agent.py`, `cadex_blueprint.py`,
`docs/BLENDER.md`, `docs/DECISIONS.md` (ADR-172).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 268cbee80aefa415519365d66c7d23529d1f5a5d

## State Impact

- target: shy-crane-2573 — the startup viewport now opens with cavity shading on, gizmos off, and overlays on but bare (no floor, no grid, only the Z axis); the gate and cadex_blueprint.PRODUCT_LOOK pin the new look (ADR-172)
